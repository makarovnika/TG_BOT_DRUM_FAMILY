"""Сервис регистрации/поиска пользователей.

Связывает три источника:
- SQLite (наша БД, маппинг Telegram_ID ↔ YClients_client_id);
- YClients API (источник правды по клиентам школы);
- логику нормализации телефона (чтобы один и тот же номер в разных форматах
  не плодил дубликатов).

Чистая бизнес-логика, без зависимостей от aiogram. Тестируется независимо.
"""

from __future__ import annotations

import re

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import User
from src.yclients.client import YClientsClient

log = structlog.get_logger("services.user")


def normalize_phone(raw: str) -> str | None:
    """Нормализует телефон к каноничному формату `+<digits>`.

    Правила:
    - всё, кроме цифр, выбрасывается;
    - 11 цифр, начинаются с 7 или 8 → `+7XXXXXXXXXX` (российский);
    - 10 цифр → `+7` + 10 цифр (тоже российский, без кода страны);
    - 10..15 цифр → `+<digits>` (международный);
    - иначе — None.

    Школа в Томске, поэтому биас в сторону РФ. Если ученик из-за рубежа,
    он сам впишет с `+` — попадёт в международную ветку.
    """
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits[0] in {"7", "8"}:
        return "+7" + digits[1:]
    if len(digits) == 10:
        return "+7" + digits
    if 10 <= len(digits) <= 15:
        return "+" + digits
    return None


class UserService:
    """Регистрация и поиск пользователей. Один инстанс на один HTTP-запрос
    (по факту — на одно входящее событие бота), потому что внутри живая
    AsyncSession SQLAlchemy."""

    def __init__(self, *, session: AsyncSession, yclients: YClientsClient) -> None:
        self._session = session
        self._yclients = yclients

    async def find_by_telegram_id(self, telegram_id: int) -> User | None:
        """Возвращает существующего пользователя из SQLite или None."""
        return await self._session.get(User, telegram_id)

    async def register(self, *, telegram_id: int, name: str, phone: str) -> User:
        """Регистрирует пользователя:

        1. Ищем клиента в YClients по телефону;
        2. Если нет — создаём;
        3. Сохраняем связку (telegram_id, yclients_client_id, name, phone) в SQLite.

        Если пользователь уже есть в SQLite — обновляем поля (имя/телефон могли
        измениться) и возвращаем. Это безопасно: телефон у нас в каноническом
        формате, дубликатов клиента в YClients не плодим.
        """
        log.info("user.register.start", telegram_id=telegram_id, phone_prefix=phone[:4])

        yc_client = await self._yclients.search_client(phone=phone)
        if yc_client is None:
            log.info("user.register.creating_in_yclients", telegram_id=telegram_id)
            yc_client = await self._yclients.create_client(name=name, phone=phone)
        else:
            log.info(
                "user.register.found_in_yclients",
                telegram_id=telegram_id,
                yclients_client_id=yc_client.id,
            )

        user = await self._session.get(User, telegram_id)
        if user is None:
            user = User(
                telegram_id=telegram_id,
                yclients_client_id=yc_client.id,
                full_name=name,
                phone=phone,
            )
            self._session.add(user)
        else:
            user.yclients_client_id = yc_client.id
            user.full_name = name
            user.phone = phone

        await self._session.commit()
        log.info("user.register.done", telegram_id=telegram_id, yclients_client_id=yc_client.id)
        return user
