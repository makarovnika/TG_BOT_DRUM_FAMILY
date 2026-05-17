"""Точка входа для бота.

Минимальная версия для фичи setup-000: только команда /start.
Логика регистрации, записи и т. д. — в следующих фичах.
"""

import asyncio
import logging

import structlog
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.config import get_settings


def configure_logging(level: str) -> None:
    """Настраивает structlog: JSON-формат, понятный и людям, и парсерам логов."""
    logging.basicConfig(level=level.upper())
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ]
    )


dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_name = message.from_user.full_name if message.from_user else "друг"
    await message.answer(
        f"Привет, {user_name}! Я бот школы барабанов.\n"
        "Пока я умею только здороваться — остальное появится в следующих обновлениях."
    )


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    log = structlog.get_logger()
    log.info("bot.starting")

    bot = Bot(token=settings.bot_token)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
