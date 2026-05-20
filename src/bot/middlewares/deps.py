"""Middleware, пробрасывающий зависимости в обработчики.

aiogram 3.x умеет инжектировать в обработчики любые именованные аргументы,
которые middleware кладёт в `data`. Так в `cmd_start(msg, user_service)`
параметр `user_service` приходит сам.

На каждое входящее событие:
- открываем новую async-сессию SQLAlchemy (через `async with`),
- собираем `UserService` поверх сессии и общего YClients-клиента,
- кладём оба в data,
- после обработки сессия автоматически закрывается.

YClients-клиент один на всё приложение — у него внутри httpx.AsyncClient,
который безопасно переиспользуется и кэширует соединения.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.reminders import RemindersScheduler
from src.services.user_service import UserService
from src.yclients.client import YClientsClient


class DepsMiddleware(BaseMiddleware):
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        yclients: YClientsClient,
        reminders: RemindersScheduler,
    ) -> None:
        self._session_factory = session_factory
        self._yclients = yclients
        self._reminders = reminders

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self._session_factory() as session:
            data["session"] = session
            data["user_service"] = UserService(session=session, yclients=self._yclients)
            # YClients-клиент инжектится напрямую — обработчики, работающие с
            # его данными в обход сервисов (профиль, мои занятия), используют его.
            data["yclients"] = self._yclients
            # Scheduler — для booking (планируем) и my_bookings (отменяем).
            data["reminders"] = self._reminders
            return await handler(event, data)
