"""Тесты YClients-клиента на respx-моках.

Покрытие:
- auth() возвращает и кэширует user_token;
- get_services / get_staff / search_client / create_client парсят ответы корректно;
- 401 → refresh user_token + повтор;
- 429 → backoff + повтор;
- 5xx → retry, после исчерпания — YClientsServerError;
- 4xx (кроме 401/429) → YClientsClientError без ретраев.

backoff_base=0 — чтобы тесты не спали.
"""

from collections.abc import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
import respx

from src.yclients.client import BASE_URL, YClientsClient
from src.yclients.exceptions import (
    YClientsAuthError,
    YClientsClientError,
    YClientsServerError,
)

# ---------- фикстуры ----------


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[YClientsClient, None]:
    """Legacy-режим: логин/пароль → POST /auth → динамический user_token."""
    c = YClientsClient(
        partner_token="partner_test",
        user_login="login@test",
        user_password="password",
        company_id=12345,
        max_retries=3,
        backoff_base=0,
    )
    yield c
    await c.close()


@pytest_asyncio.fixture
async def static_client() -> AsyncGenerator[YClientsClient, None]:
    """Новый режим: статический User Token из «Доступ к API»."""
    c = YClientsClient(
        partner_token="partner_test",
        user_token="static_xyz",
        company_id=12345,
        max_retries=3,
        backoff_base=0,
    )
    yield c
    await c.close()


def _ok(json_body: dict) -> httpx.Response:
    return httpx.Response(200, json={"success": True, "data": json_body, "meta": []})


def _auth_ok(token: str = "user_token_123") -> httpx.Response:
    return _ok({"id": 1, "user_token": token, "name": "Admin"})


# ---------- auth ----------


async def test_auth_returns_user_token_and_is_forced(client: YClientsClient) -> None:
    """`auth()` — принудительный: дёргает /auth каждый раз, не кэширует."""
    with respx.mock(base_url=BASE_URL) as mock:
        route = mock.post("/auth").mock(return_value=_auth_ok("tkn_abc"))

        token = await client.auth()
        await client.auth()

        assert token == "tkn_abc"
        assert route.call_count == 2


async def test_auth_failure_raises(client: YClientsClient) -> None:
    bad_auth = httpx.Response(401, json={"meta": {"message": "Invalid login"}})
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/auth").mock(return_value=bad_auth)
        with pytest.raises(YClientsAuthError):
            await client.auth()


# ---------- читающие методы ----------


async def test_get_services_parses_response(client: YClientsClient) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/auth").mock(return_value=_auth_ok())
        mock.get("/book_services/12345").mock(
            return_value=httpx.Response(
                200,
                json={
                    "success": True,
                    "data": {
                        "services": [
                            {
                                "id": 1,
                                "title": "Индивидуальное занятие",
                                "price_min": 1500,
                                "price_max": 1500,
                                "duration": 3600,
                            },
                            {"id": 2, "title": "Групповое", "duration": 5400},
                        ],
                        "category": [],
                    },
                    "meta": [],
                },
            )
        )

        services = await client.get_services()

        assert len(services) == 2
        assert services[0].title == "Индивидуальное занятие"
        assert services[0].duration == 3600
        assert services[1].id == 2


async def test_get_staff_parses_response(client: YClientsClient) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/auth").mock(return_value=_auth_ok())
        mock.get("/book_staff/12345").mock(
            return_value=httpx.Response(
                200,
                json={
                    "success": True,
                    "data": [
                        {"id": 10, "name": "Иван", "specialization": "Барабаны"},
                        {"id": 20, "name": "Пётр"},
                    ],
                    "meta": [],
                },
            )
        )

        staff = await client.get_staff()

        assert len(staff) == 2
        assert staff[0].name == "Иван"
        assert staff[0].specialization == "Барабаны"
        assert staff[1].specialization is None


async def test_search_client_returns_first_match(client: YClientsClient) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/auth").mock(return_value=_auth_ok())
        mock.get("/clients/12345").mock(
            return_value=httpx.Response(
                200,
                json={
                    "success": True,
                    "data": [
                        {"id": 555, "name": "Иван Петров", "phone": "+79991112233"},
                    ],
                    "meta": [],
                },
            )
        )

        c = await client.search_client(phone="+79991112233")

        assert c is not None
        assert c.id == 555
        assert c.name == "Иван Петров"


async def test_search_client_returns_none_when_empty(client: YClientsClient) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/auth").mock(return_value=_auth_ok())
        mock.get("/clients/12345").mock(
            return_value=httpx.Response(200, json={"success": True, "data": [], "meta": []})
        )

        c = await client.search_client(phone="+79991112233")

        assert c is None


async def test_create_client_returns_created(client: YClientsClient) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/auth").mock(return_value=_auth_ok())
        mock.post("/clients/12345").mock(
            return_value=httpx.Response(
                200,
                json={
                    "success": True,
                    "data": {"id": 777, "name": "Новый", "phone": "+79990000000"},
                    "meta": [],
                },
            )
        )

        c = await client.create_client(name="Новый", phone="+79990000000")

        assert c.id == 777
        assert c.name == "Новый"


# ---------- error handling ----------


async def test_401_triggers_refresh_and_retry(client: YClientsClient) -> None:
    """Сценарий: auth ОК → запрос отдаёт 401 → клиент делает повторный auth → запрос ОК."""
    auth_responses = [_auth_ok("first_token"), _auth_ok("second_token")]
    ok_services = httpx.Response(
        200,
        json={"success": True, "data": {"services": [{"id": 1, "title": "OK"}]}, "meta": []},
    )
    services_responses = [
        httpx.Response(401, json={"meta": {"message": "Token expired"}}),
        ok_services,
    ]

    with respx.mock(base_url=BASE_URL) as mock:
        auth_route = mock.post("/auth").mock(side_effect=auth_responses)
        services_route = mock.get("/book_services/12345").mock(side_effect=services_responses)

        services = await client.get_services()

        assert len(services) == 1
        assert services[0].title == "OK"
        # auth дёрнули дважды: первый раз перед запросом, второй после 401.
        assert auth_route.call_count == 2
        # services тоже дважды: первый раз 401, потом 200.
        assert services_route.call_count == 2


async def test_429_retried_with_backoff(client: YClientsClient) -> None:
    """429 → повтор. На второй попытке всё ок."""
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/auth").mock(return_value=_auth_ok())
        services_route = mock.get("/book_services/12345").mock(
            side_effect=[
                httpx.Response(429),
                httpx.Response(
                    200,
                    json={
                        "success": True,
                        "data": {"services": [{"id": 1, "title": "После 429"}]},
                        "meta": [],
                    },
                ),
            ]
        )

        services = await client.get_services()

        assert services[0].title == "После 429"
        assert services_route.call_count == 2


async def test_5xx_retried_then_raises_after_exhaust(client: YClientsClient) -> None:
    """3 попытки → 3 пятисотых → YClientsServerError."""
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/auth").mock(return_value=_auth_ok())
        services_route = mock.get("/book_services/12345").mock(return_value=httpx.Response(503))

        with pytest.raises(YClientsServerError):
            await client.get_services()

        # max_retries=3 в фикстуре
        assert services_route.call_count == 3


async def test_400_not_retried(client: YClientsClient) -> None:
    """4xx (кроме 401/429) — без ретраев, сразу исключение."""
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/auth").mock(return_value=_auth_ok())
        services_route = mock.get("/book_services/12345").mock(
            return_value=httpx.Response(400, json={"meta": {"errors": "bad request"}})
        )

        with pytest.raises(YClientsClientError):
            await client.get_services()

        assert services_route.call_count == 1


# ---------- заголовки ----------


async def test_request_includes_both_tokens_in_authorization(client: YClientsClient) -> None:
    """Проверяем формат `Bearer {partner}, User {user}`."""
    captured: dict[str, str] = {}

    def capture(request: httpx.Request) -> httpx.Response:
        captured["Authorization"] = request.headers.get("Authorization", "")
        captured["Accept"] = request.headers.get("Accept", "")
        return httpx.Response(200, json={"success": True, "data": {"services": []}, "meta": []})

    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/auth").mock(return_value=_auth_ok("USR123"))
        mock.get("/book_services/12345").mock(side_effect=capture)

        await client.get_services()

    assert captured["Authorization"] == "Bearer partner_test, User USR123"
    assert captured["Accept"] == "application/vnd.api.v2+json"


# ---------- static user_token mode ----------


async def test_static_token_skips_auth_call(static_client: YClientsClient) -> None:
    """В статическом режиме /auth никогда не дёргается.

    `/auth` не регистрируем намеренно — если клиент его всё-таки дёрнет,
    respx упадёт с «no matching route», и тест честно покажет ошибку.
    """
    ok = httpx.Response(
        200,
        json={"success": True, "data": {"services": [{"id": 1, "title": "X"}]}, "meta": []},
    )
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/book_services/12345").mock(return_value=ok)

        services = await static_client.get_services()

        assert len(services) == 1
        assert services[0].title == "X"


async def test_static_token_authorization_header(static_client: YClientsClient) -> None:
    """Статический токен попадает в заголовок ровно как `User {value}`."""
    captured: dict[str, str] = {}

    def capture(request: httpx.Request) -> httpx.Response:
        captured["Authorization"] = request.headers.get("Authorization", "")
        return httpx.Response(200, json={"success": True, "data": {"services": []}, "meta": []})

    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/book_services/12345").mock(side_effect=capture)
        await static_client.get_services()

    assert captured["Authorization"] == "Bearer partner_test, User static_xyz"


async def test_static_token_401_raises_without_refresh(static_client: YClientsClient) -> None:
    """В статическом режиме 401 сразу бросает YClientsAuthError — нечем рефрешить.

    `/auth` не регистрируем — если клиент попробует туда сходить (что было бы
    багом в статическом режиме), respx покажет это «no matching route».
    """
    with respx.mock(base_url=BASE_URL) as mock:
        services_route = mock.get("/book_services/12345").mock(return_value=httpx.Response(401))

        with pytest.raises(YClientsAuthError):
            await static_client.get_services()

        # services дёрнулся ровно один раз — никаких ретраев на 401 в статическом режиме.
        assert services_route.call_count == 1


async def test_auth_method_fails_in_static_mode(static_client: YClientsClient) -> None:
    """`auth()` имеет смысл только при наличии логина/пароля."""
    with pytest.raises(YClientsAuthError):
        await static_client.auth()


async def test_constructor_raises_without_any_credentials() -> None:
    """Без user_token и без логина/пароля — ValueError на этапе создания."""
    with pytest.raises(ValueError, match="user_token"):
        YClientsClient(partner_token="x", company_id=1)
