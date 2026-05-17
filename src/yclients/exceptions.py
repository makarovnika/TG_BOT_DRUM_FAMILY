"""Типизированные исключения для YClients-клиента.

Зачем отдельные классы, а не один общий:
- 401 → надо перевыпустить user_token (обработает сам клиент);
- 429 → надо подождать и повторить;
- 5xx → надо повторить с backoff;
- 4xx (кроме 401, 429) → клиентская ошибка, повторять смысла нет —
  пользователю показываем «что-то не так, проверь данные».
Разные ветви обработки нагляднее всего на разных типах исключений.
"""


class YClientsError(Exception):
    """Базовый класс всех ошибок YClients API."""

    def __init__(self, message: str, *, status_code: int | None = None, payload: object = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class YClientsAuthError(YClientsError):
    """401 или невалидные логин/пароль/партнёрский токен."""


class YClientsRateLimited(YClientsError):
    """429 — превышен лимит запросов."""


class YClientsServerError(YClientsError):
    """5xx — YClients недоступен. Также бросается после исчерпания ретраев."""


class YClientsClientError(YClientsError):
    """Прочие 4xx — невалидный запрос, не найдено и т. п."""
