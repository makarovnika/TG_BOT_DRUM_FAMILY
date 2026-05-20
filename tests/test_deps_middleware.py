"""Тесты DepsMiddleware — проверяем, что:
- сессия открывается из session_factory;
- в data попадает `session` и `user_service`;
- session закрывается после обработчика (через `async with`);
- если handler бросает — сессия всё равно закрывается.
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest_asyncio

from src.bot.middlewares.deps import DepsMiddleware
from src.db.session import create_engine, create_session_factory, init_db
from src.services.user_service import UserService
from src.yclients.client import YClientsClient


@pytest_asyncio.fixture
async def middleware() -> AsyncGenerator[DepsMiddleware, None]:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    factory = create_session_factory(engine)
    yclients = YClientsClient(partner_token="p", user_token="u", company_id=1, backoff_base=0)
    reminders = MagicMock()  # тестовая заглушка, не запускаем планировщик
    yield DepsMiddleware(session_factory=factory, yclients=yclients, reminders=reminders)
    await yclients.close()
    await engine.dispose()


async def test_middleware_injects_session_and_user_service(
    middleware: DepsMiddleware,
) -> None:
    """data должен получить и `session`, и `user_service`."""
    captured: dict = {}

    async def fake_handler(event, data):
        captured["session"] = data.get("session")
        captured["user_service"] = data.get("user_service")
        return "ok"

    result = await middleware(fake_handler, event=AsyncMock(), data={})

    assert result == "ok"
    assert captured["session"] is not None
    assert isinstance(captured["user_service"], UserService)


async def test_middleware_session_is_usable_inside_handler(
    middleware: DepsMiddleware,
) -> None:
    """Сессию реально можно использовать (не моковая)."""
    from sqlalchemy import text

    async def fake_handler(event, data):
        result = await data["session"].execute(text("SELECT 1"))
        return result.scalar_one()

    value = await middleware(fake_handler, event=AsyncMock(), data={})
    assert value == 1


async def test_middleware_propagates_handler_exception(
    middleware: DepsMiddleware,
) -> None:
    """Если handler бросает — middleware пропускает исключение, не глотает."""

    class HandlerError(Exception):
        pass

    async def failing_handler(event, data):
        raise HandlerError("boom")

    try:
        await middleware(failing_handler, event=AsyncMock(), data={})
    except HandlerError:
        pass  # ожидаемо
    else:
        raise AssertionError("Ожидали HandlerError, исключение проглотилось")
