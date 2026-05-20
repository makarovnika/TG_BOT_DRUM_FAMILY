"""Обработчик профиля пользователя.

Достаёт пользователя из SQLite, по `yclients_client_id` тянет полную
карточку из YClients и форматирует.

Что показываем:
- имя (display_name из YClients);
- телефон, email;
- количество посещений;
- баланс (если есть долг — подсвечиваем);
- абонементы НЕ показываем — endpoint /loyalty/abonements/{cid} вернул 404
  на школе Drum Family. Возможно, у школы оплата за каждое занятие, без
  абонементной модели. Когда выяснится — добавим.

ВАЖНО: после Phase 1 (брендовый рестайл) кнопка «👤 Мой профиль» убрана
из главного меню. Профиль теперь доступен только через команду /profile,
которая вызывает `show_profile` напрямую из `commands.py`. Поэтому здесь
НЕТ Router и НЕТ @router.message-декоратора — это бы создавало мёртвый
handler, который никогда не сработает.
"""

import structlog
from aiogram.types import Message

from src.bot import texts
from src.bot.utils import escape_html
from src.services.user_service import UserService
from src.yclients.client import YClientsClient
from src.yclients.exceptions import YClientsError
from src.yclients.models import Client

log = structlog.get_logger("handlers.profile")


async def show_profile(
    message: Message,
    user_service: UserService,
    yclients: YClientsClient,
) -> None:
    if message.from_user is None:
        return

    user = await user_service.find_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer(texts.PROFILE_NEED_REGISTRATION)
        return

    if user.yclients_client_id is None:
        await message.answer(texts.PROFILE_NOT_LINKED)
        return

    try:
        client = await yclients.get_client_by_id(user.yclients_client_id)
    except YClientsError as exc:
        log.warning("profile.yclients_error", error=str(exc))
        await message.answer(texts.PROFILE_FETCH_ERROR)
        return

    await message.answer(_format_profile(client), parse_mode="HTML")


def _format_profile(c: Client) -> str:
    """Собирает человекочитаемый профиль с минимумом нюансов.

    Используем HTML вместо Markdown, потому что в именах/email могут быть
    спецсимволы (`_`, `*`), которые Markdown ломают.
    """
    name = c.display_name or c.name
    parts = [f"<b>👤 {escape_html(name)}</b>"]
    parts.append("")
    parts.append(f"📞 Телефон: <code>{escape_html(c.phone)}</code>")
    if c.email:
        parts.append(f"✉️ Email: <code>{escape_html(c.email)}</code>")
    parts.append("")

    if c.visits is not None:
        parts.append(f"🥁 Посещений: <b>{c.visits}</b>")

    if c.balance is not None:
        if c.balance < 0:
            # Отрицательный баланс — долг. spent − paid > 0.
            parts.append(f"💰 Баланс: <b>{c.balance:+} ₽</b> (долг — обратись к админу для оплаты)")
        elif c.balance > 0:
            parts.append(f"💰 Баланс: <b>+{c.balance} ₽</b> (предоплата)")
        else:
            parts.append("💰 Баланс: <b>0 ₽</b>")

    if c.spent is not None and c.paid is not None and (c.spent or c.paid):
        parts.append(f"\n<i>Всего в школе: оплачено {c.paid} ₽ из {c.spent} ₽ начислений</i>")

    return "\n".join(parts)
