"""Async-клиент YClients API.

Главные идеи:
- два токена в одном заголовке: `Bearer {partner}, User {user}`
  (см. https://developers.yclients.com/ru/);
- `user_token` получаем сами через POST /auth и кэшируем в инстансе клиента;
  если приходит 401 — токен протух, перевыпускаем и повторяем запрос;
- 429 → ждём (экспоненциальный backoff) и повторяем;
- 5xx → ждём и повторяем; после исчерпания попыток бросаем YClientsServerError;
- 4xx (кроме 401/429) → YClientsClientError, без ретраев.

Клиент — async context manager, использовать так:

    async with YClientsClient(...) as yc:
        services = await yc.get_services()
"""

from __future__ import annotations

import asyncio
from types import TracebackType
from typing import Any

import httpx
import structlog

from src.yclients.exceptions import (
    YClientsAuthError,
    YClientsClientError,
    YClientsError,
    YClientsRateLimited,
    YClientsServerError,
)
from src.yclients.models import AuthResponse, Client, Service, Staff

BASE_URL = "https://api.yclients.com/api/v1"

log = structlog.get_logger("yclients.client")


class YClientsClient:
    def __init__(
        self,
        *,
        partner_token: str,
        company_id: int,
        user_token: str | None = None,
        user_login: str | None = None,
        user_password: str | None = None,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_base: float = 1.0,
    ) -> None:
        """Два режима аутентификации:

        - **Статический user_token** (рекомендуется): передай `user_token`
          (например, токен системного пользователя из «Доступ к API»).
          Тогда /auth никогда не вызывается, а на 401 сразу бросается
          YClientsAuthError (программно его не починить).
        - **Логин/пароль**: передай `user_login` + `user_password`. Клиент
          сам сделает POST /auth и будет автоматически перевыпускать токен
          при 401.

        Параметры:
        - `partner_token`: постоянный, с developers.yclients.com («Общая информация»).
        - `company_id`: ID филиала.
        - `timeout`: на один HTTP-запрос.
        - `max_retries`: общее число попыток на 429/5xx (для 401 — отдельно).
        - `backoff_base`: множитель `asyncio.sleep(backoff_base * 2**attempt)`.
          В тестах ставим 0, чтобы не спать по-настоящему.
        """
        if not user_token and not (user_login and user_password):
            raise ValueError(
                "YClientsClient: нужен либо user_token, либо пара user_login + user_password"
            )

        self._partner_token = partner_token
        self._user_login = user_login
        self._user_password = user_password
        self._company_id = company_id
        self._max_retries = max_retries
        self._backoff_base = backoff_base

        # Если передан статический user_token — сразу кладём его, /auth не нужен.
        self._user_token: str | None = user_token
        self._http = httpx.AsyncClient(base_url=BASE_URL, timeout=timeout)
        # Защищает от гонки: два корутины не должны одновременно дёргать /auth.
        self._auth_lock = asyncio.Lock()

    @property
    def _can_refresh_token(self) -> bool:
        """True, если у нас есть логин/пароль и можем сделать POST /auth."""
        return bool(self._user_login and self._user_password)

    @property
    def company_id(self) -> int:
        return self._company_id

    async def __aenter__(self) -> YClientsClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        await self._http.aclose()

    # ---------- внутреннее ----------

    def _headers(self, *, with_user: bool) -> dict[str, str]:
        auth = f"Bearer {self._partner_token}"
        if with_user and self._user_token:
            auth += f", User {self._user_token}"
        return {
            "Authorization": auth,
            "Accept": "application/vnd.api.v2+json",
            "Content-Type": "application/json",
        }

    async def _backoff(self, attempt: int) -> None:
        """Экспоненциальный backoff. attempt=0 → 1*base, =1 → 2*base, =2 → 4*base."""
        delay = self._backoff_base * (2**attempt)
        if delay > 0:
            await asyncio.sleep(delay)

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Универсальная обёртка над httpx с retry/refresh.

        Поведение по статусам:
        - 200 → возвращаем JSON;
        - 401 → перевыпускаем user_token и повторяем (не считается ретраем);
        - 429 → backoff, считается ретраем;
        - 5xx → backoff, считается ретраем;
        - другие 4xx → YClientsClientError, ретраев нет.
        После `max_retries` неудачных попыток — YClientsServerError или
        YClientsRateLimited (в зависимости от последнего статуса).
        """
        last_exception: YClientsError | None = None
        # 401 не считается ретраем, поэтому отдельный счётчик.
        auth_retries_left = 1

        for attempt in range(self._max_retries):
            if self._user_token is None:
                await self._ensure_authed()

            try:
                response = await self._http.request(
                    method,
                    path,
                    headers=self._headers(with_user=True),
                    **kwargs,
                )
            except httpx.HTTPError as exc:
                last_exception = YClientsServerError(f"HTTP error talking to YClients: {exc}")
                log.warning("yclients.network_error", attempt=attempt, error=str(exc))
                await self._backoff(attempt)
                continue

            status = response.status_code

            if status == 200:
                return response.json()

            if status == 401 and auth_retries_left > 0 and self._can_refresh_token:
                auth_retries_left -= 1
                log.info("yclients.user_token_expired", refreshing=True)
                self._user_token = None
                await self._ensure_authed()
                continue  # повтор без увеличения attempt — это не "ретрай"

            if status == 401:
                # Либо нет логина/пароля (статический режим), либо refresh
                # уже пробовали и снова получили 401 — программно не починить.
                raise YClientsAuthError(
                    "401 от YClients — user_token невалиден или нет нужных прав",
                    status_code=401,
                    payload=_safe_json(response),
                )

            if status == 429:
                last_exception = YClientsRateLimited(
                    "429 Too Many Requests",
                    status_code=429,
                    payload=_safe_json(response),
                )
                log.warning("yclients.rate_limited", attempt=attempt)
                await self._backoff(attempt)
                continue

            if 500 <= status < 600:
                last_exception = YClientsServerError(
                    f"{status} от YClients",
                    status_code=status,
                    payload=_safe_json(response),
                )
                log.warning("yclients.server_error", attempt=attempt, status=status)
                await self._backoff(attempt)
                continue

            # Остальные 4xx — клиентская ошибка, ретраи не помогут.
            raise YClientsClientError(
                f"{status} от YClients: {_safe_json(response)}",
                status_code=status,
                payload=_safe_json(response),
            )

        # Все попытки исчерпаны.
        assert last_exception is not None
        raise last_exception

    async def _ensure_authed(self) -> None:
        """Идемпотентно: если токена нет — получает; иначе ничего не делает.

        В статическом режиме (user_token задан при создании) сюда мы попадаем
        только если кто-то вручную сбросил self._user_token — и тогда без
        логина/пароля идти на /auth бессмысленно: бросаем YClientsAuthError.
        """
        async with self._auth_lock:
            if self._user_token is not None:
                return
            if not self._can_refresh_token:
                raise YClientsAuthError(
                    "user_token пуст и нет логина/пароля для refresh — нечего делать"
                )
            await self._auth_locked()

    async def _auth_locked(self) -> None:
        """Реальный вызов POST /auth. Должен вызываться под self._auth_lock."""
        response = await self._http.post(
            "/auth",
            headers=self._headers(with_user=False),
            json={"login": self._user_login, "password": self._user_password},
        )
        if response.status_code != 200:
            raise YClientsAuthError(
                f"/auth вернул {response.status_code}",
                status_code=response.status_code,
                payload=_safe_json(response),
            )
        parsed = AuthResponse.model_validate(response.json()["data"])
        self._user_token = parsed.user_token
        log.info("yclients.authed", user_id=parsed.id)

    # ---------- публичное API ----------

    async def auth(self) -> str:
        """Получает user_token принудительно (даже если уже есть).

        В статическом режиме (user_token задан при создании, но нет
        логина/пароля) бросает YClientsAuthError — обновлять нечем.
        """
        if not self._can_refresh_token:
            raise YClientsAuthError("auth() недоступен в статическом режиме (нет логина/пароля)")
        async with self._auth_lock:
            self._user_token = None
            await self._auth_locked()
        assert self._user_token is not None
        return self._user_token

    async def get_services(self) -> list[Service]:
        """GET /book_services/{company_id} — список услуг для записи."""
        payload = await self._request("GET", f"/book_services/{self._company_id}")
        # YClients иногда возвращает {"services": [...], "category": [...]},
        # иногда — массив сразу. Поддерживаем оба варианта.
        data = payload["data"]
        services = data["services"] if isinstance(data, dict) else data
        return [Service.model_validate(item) for item in services]

    async def get_staff(self) -> list[Staff]:
        """GET /book_staff/{company_id} — список преподавателей."""
        payload = await self._request("GET", f"/book_staff/{self._company_id}")
        return [Staff.model_validate(item) for item in payload["data"]]

    async def search_client(self, phone: str) -> Client | None:
        """GET /clients/{company_id} с фильтром по телефону.

        Возвращает первого найденного клиента или None. Если совпадений несколько,
        предполагаем что нам важен любой (телефон в YClients обычно уникален).
        """
        payload = await self._request(
            "GET",
            f"/clients/{self._company_id}",
            params={"phone": phone},
        )
        clients = payload["data"]
        if not clients:
            return None
        return Client.model_validate(clients[0])

    async def create_client(self, *, name: str, phone: str, email: str | None = None) -> Client:
        """POST /clients/{company_id} — создаёт нового клиента."""
        body: dict[str, Any] = {"name": name, "phone": phone}
        if email:
            body["email"] = email
        payload = await self._request(
            "POST",
            f"/clients/{self._company_id}",
            json=body,
        )
        return Client.model_validate(payload["data"])


def _safe_json(response: httpx.Response) -> object:
    """Пытается распарсить тело как JSON, в случае неудачи возвращает текст."""
    try:
        return response.json()
    except ValueError:
        return response.text
