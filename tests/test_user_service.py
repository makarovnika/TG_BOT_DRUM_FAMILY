"""Тесты `UserService` и `normalize_phone`.

DB — in-memory SQLite (как в test_db.py).
YClients — respx-моки.
"""

from collections.abc import AsyncGenerator

import httpx
import pytest_asyncio
import respx
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import User
from src.db.session import create_engine, create_session_factory, init_db
from src.services.user_service import UserService, normalize_phone
from src.yclients.client import BASE_URL, YClientsClient

# ---------- normalize_phone ----------


def test_normalize_phone_russian_with_8() -> None:
    assert normalize_phone("89991112233") == "+79991112233"


def test_normalize_phone_russian_with_plus_7() -> None:
    assert normalize_phone("+79991112233") == "+79991112233"


def test_normalize_phone_russian_without_country_code() -> None:
    assert normalize_phone("9991112233") == "+79991112233"


def test_normalize_phone_strips_formatting() -> None:
    assert normalize_phone("+7 (999) 111-22-33") == "+79991112233"
    assert normalize_phone("8 999 111 22 33") == "+79991112233"


def test_normalize_phone_international() -> None:
    # Беларусь, 12 цифр — попадает в общую международную ветку.
    assert normalize_phone("+375291234567") == "+375291234567"


def test_normalize_phone_too_short() -> None:
    assert normalize_phone("123") is None
    assert normalize_phone("") is None


def test_normalize_phone_too_long() -> None:
    assert normalize_phone("1234567890123456") is None  # 16 цифр


# ---------- UserService ----------


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    factory = create_session_factory(engine)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def yclients() -> AsyncGenerator[YClientsClient, None]:
    c = YClientsClient(
        partner_token="partner_test",
        user_token="static_xyz",
        company_id=12345,
        backoff_base=0,
    )
    yield c
    await c.close()


async def test_find_by_telegram_id_returns_none_when_missing(
    session: AsyncSession,
    yclients: YClientsClient,
) -> None:
    svc = UserService(session=session, yclients=yclients)
    assert await svc.find_by_telegram_id(99999) is None


async def test_register_creates_in_yclients_when_not_found(
    session: AsyncSession,
    yclients: YClientsClient,
) -> None:
    """Телефон не найден в YClients → создаём через create_client → сохраняем в SQLite."""
    svc = UserService(session=session, yclients=yclients)

    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/clients/12345").mock(
            return_value=httpx.Response(200, json={"success": True, "data": [], "meta": []})
        )
        create_route = mock.post("/clients/12345").mock(
            return_value=httpx.Response(
                200,
                json={
                    "success": True,
                    "data": {"id": 777, "name": "Иван", "phone": "+79991112233"},
                    "meta": [],
                },
            )
        )

        user = await svc.register(telegram_id=12345, name="Иван", phone="+79991112233")

        assert user.telegram_id == 12345
        assert user.yclients_client_id == 777
        assert user.full_name == "Иван"
        assert user.phone == "+79991112233"
        assert create_route.call_count == 1

    # Проверяем, что реально сохранилось в БД.
    from_db = await session.get(User, 12345)
    assert from_db is not None
    assert from_db.yclients_client_id == 777


async def test_register_uses_existing_yclients_client(
    session: AsyncSession,
    yclients: YClientsClient,
) -> None:
    """Телефон найден в YClients → используем найденный, create НЕ дёргается."""
    svc = UserService(session=session, yclients=yclients)

    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/clients/12345").mock(
            return_value=httpx.Response(
                200,
                json={
                    "success": True,
                    "data": [
                        {"id": 555, "name": "Существующий", "phone": "+79991112233"},
                    ],
                    "meta": [],
                },
            )
        )
        # create регистрируем, но НЕ ожидаем вызова — поэтому assert_all_called=False
        # не нужен: respx по умолчанию требует все routes, но мы убедимся через call_count.
        # Чтобы не падать на «route was not called», просто не регистрируем POST вообще:
        # тогда если кто-то его попытается дёрнуть, respx выдаст «no matching route»
        # и тест честно упадёт.

        user = await svc.register(telegram_id=12345, name="Новое имя", phone="+79991112233")

        # Берём ID существующего клиента, имя записываем то, что прислал пользователь.
        assert user.yclients_client_id == 555
        assert user.full_name == "Новое имя"


async def test_register_updates_existing_user_in_db(
    session: AsyncSession,
    yclients: YClientsClient,
) -> None:
    """Если User уже есть в SQLite (например, перерегистрация) — обновляем поля."""
    # Заранее кладём «старого» пользователя
    session.add(User(telegram_id=12345, full_name="Старое имя", phone="+70000000000"))
    await session.commit()

    svc = UserService(session=session, yclients=yclients)

    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/clients/12345").mock(
            return_value=httpx.Response(
                200,
                json={
                    "success": True,
                    "data": [{"id": 999, "name": "Иван", "phone": "+79998887766"}],
                    "meta": [],
                },
            )
        )

        user = await svc.register(telegram_id=12345, name="Иван", phone="+79998887766")

        assert user.yclients_client_id == 999
        assert user.full_name == "Иван"
        assert user.phone == "+79998887766"

    # В БД действительно одна запись и с новыми полями.
    from_db = await session.get(User, 12345)
    assert from_db is not None
    assert from_db.full_name == "Иван"
    assert from_db.yclients_client_id == 999
