"""Тесты DB-слоя.

Идея: каждый тест получает чистую in-memory SQLite через фикстуру `session`.
Это:
- быстро (миллисекунды на тест);
- изолированно (тесты не влияют друг на друга);
- не требует .env и реальной базы.
"""

from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import User
from src.db.session import create_engine, create_session_factory, init_db


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    """Чистая in-memory SQLite на каждый тест.

    Почему `sqlite+aiosqlite:///:memory:` — это БД, которая живёт только
    в памяти процесса и исчезает при закрытии движка. Идеально для тестов.
    """
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    factory = create_session_factory(engine)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_create_user_minimal(session: AsyncSession) -> None:
    """Можно создать User только с telegram_id (остальные поля nullable)."""
    user = User(telegram_id=12345)
    session.add(user)
    await session.commit()

    fetched = await session.get(User, 12345)
    assert fetched is not None
    assert fetched.telegram_id == 12345
    assert fetched.yclients_client_id is None
    assert fetched.full_name is None
    assert fetched.phone is None
    assert fetched.created_at is not None
    assert fetched.updated_at is not None


async def test_create_user_full(session: AsyncSession) -> None:
    """Можно создать User со всеми полями сразу."""
    user = User(
        telegram_id=999_999_999_999,  # большое число — проверяем BigInteger
        yclients_client_id=42,
        full_name="Иван Петров",
        phone="+79123456789",
    )
    session.add(user)
    await session.commit()

    fetched = await session.get(User, 999_999_999_999)
    assert fetched is not None
    assert fetched.yclients_client_id == 42
    assert fetched.full_name == "Иван Петров"
    assert fetched.phone == "+79123456789"


async def test_update_user_yclients_id(session: AsyncSession) -> None:
    """Главный сценарий: сначала записали telegram_id, потом привязали YClients."""
    user = User(telegram_id=12345, full_name="Иван Петров")
    session.add(user)
    await session.commit()

    user.yclients_client_id = 42
    await session.commit()

    fetched = await session.get(User, 12345)
    assert fetched is not None
    assert fetched.yclients_client_id == 42


async def test_query_by_telegram_id(session: AsyncSession) -> None:
    """Поиск по telegram_id через select — основной паттерн в боте."""
    session.add(User(telegram_id=111, full_name="Один"))
    session.add(User(telegram_id=222, full_name="Два"))
    await session.commit()

    stmt = select(User).where(User.telegram_id == 222)
    result = await session.execute(stmt)
    found = result.scalar_one_or_none()

    assert found is not None
    assert found.full_name == "Два"


async def test_telegram_id_is_unique(session: AsyncSession) -> None:
    """telegram_id — первичный ключ, нельзя вставить два User с одинаковым ID."""
    session.add(User(telegram_id=12345))
    await session.commit()

    session.add(User(telegram_id=12345))
    try:
        await session.commit()
        raise AssertionError("Ожидали IntegrityError, но commit прошёл")
    except IntegrityError:
        await session.rollback()  # обязателен, чтобы сессия осталась пригодной


async def test_query_nonexistent_returns_none(session: AsyncSession) -> None:
    """session.get для несуществующего id возвращает None, а не падает."""
    fetched = await session.get(User, 99999)
    assert fetched is None
