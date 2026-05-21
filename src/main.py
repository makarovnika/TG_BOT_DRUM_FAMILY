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
from aiogram.types import BotCommand

from src.bot.handlers import (
    booking,
    commands,
    faq,
    feedback,
    menu_stub,
    my_bookings,
    registration,
    start,
    static_info,
)
from src.bot.middlewares.deps import DepsMiddleware
from src.bot.reminders import RemindersScheduler
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

    # --- Напоминания за 24ч и 1ч до занятия (ТЗ §8.13, §8.14)
    reminders = RemindersScheduler(bot)
    reminders.start()
    # set_my_commands регистрирует команды в Telegram UI — при наборе `/`
    # пользователь видит автоподсказку. Вызываем на каждом старте: если
    # описание поменялось — Telegram обновит, иначе ноп.
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="🥁 Начать"),
            BotCommand(command="trial", description="Записаться на пробный"),
            BotCommand(command="schedule", description="Моё расписание"),
            BotCommand(command="prices", description="Стоимость занятий"),
            BotCommand(command="contacts", description="Адрес и контакты"),
            BotCommand(command="faq", description="Частые вопросы"),
            BotCommand(command="admin", description="Написать администратору"),
            BotCommand(command="profile", description="Мой профиль"),
            BotCommand(command="cancel", description="Отменить текущее действие"),
            BotCommand(command="help", description="Подсказка по командам"),
        ]
    )
    dp = Dispatcher()
    dp.update.middleware(
        DepsMiddleware(
            session_factory=session_factory,
            yclients=yclients,
            reminders=reminders,
        )
    )
    # Порядок важен: специфичные команды → /start → FSM регистрации →
    # реальные обработчики меню → заглушки.
    # Это даёт правильный приоритет: /cancel ловится ВНЕ FSM, реальные
    # обработчики меню («Профиль», «Мои занятия») имеют приоритет над stubs.
    dp.include_router(commands.router)
    dp.include_router(start.router)
    dp.include_router(registration.router)
    dp.include_router(my_bookings.router)
    dp.include_router(booking.router)
    dp.include_router(faq.router)
    dp.include_router(feedback.router)
    dp.include_router(static_info.router)
    dp.include_router(menu_stub.router)

    log.info("bot.starting", company_id=settings.yclients_company_id)
    try:
        await dp.start_polling(bot)
    finally:
        log.info("bot.shutdown")
        await reminders.shutdown()
        await bot.session.close()
        await yclients.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
