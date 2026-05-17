"""Точка входа для бота.

Что собирается здесь:
- логирование (structlog в JSON);
- движок БД и фабрика сессий, миграция схемы (init_db);
- YClients-клиент (статический режим, если есть `YCLIENTS_USER_TOKEN`,
  иначе — legacy через логин/пароль);
- aiogram Bot + Dispatcher + DI-middleware + роутеры;
- корректное завершение: закрытие http-сессии, движка БД и AsyncClient YClients.
"""

import asyncio
import logging
from typing import Any

import structlog
from aiogram import Bot, Dispatcher

from src.bot.handlers import menu_stub, registration, start
from src.bot.middlewares.deps import DepsMiddleware
from src.config import Settings, get_settings
from src.db.session import create_engine, create_session_factory, init_db
from src.yclients.client import YClientsClient


def configure_logging(level: str) -> None:
    """structlog в JSON — удобно и читать, и парсить в проде."""
    logging.basicConfig(level=level.upper())
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ]
    )


def build_yclients_client(settings: Settings) -> YClientsClient:
    """Собирает YClientsClient в правильном режиме.

    Если в `.env` есть `YCLIENTS_USER_TOKEN` — статический режим (рекомендуется).
    Иначе — пара логин/пароль и динамический user_token через /auth.
    """
    common_kwargs: dict[str, Any] = {
        "partner_token": settings.yclients_partner_token,
        "company_id": settings.yclients_company_id,
    }
    if settings.yclients_user_token:
        return YClientsClient(user_token=settings.yclients_user_token, **common_kwargs)
    return YClientsClient(
        user_login=settings.yclients_user_login,
        user_password=settings.yclients_user_password,
        **common_kwargs,
    )


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    log = structlog.get_logger()

    # --- БД
    engine = create_engine(settings.database_url)
    await init_db(engine)
    session_factory = create_session_factory(engine)

    # --- YClients
    yclients = build_yclients_client(settings)

    # --- Telegram-бот
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.update.middleware(DepsMiddleware(session_factory=session_factory, yclients=yclients))
    dp.include_router(start.router)
    dp.include_router(registration.router)
    dp.include_router(menu_stub.router)

    log.info("bot.starting", company_id=settings.yclients_company_id)
    try:
        await dp.start_polling(bot)
    finally:
        log.info("bot.shutdown")
        await bot.session.close()
        await yclients.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
