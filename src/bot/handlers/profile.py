"""Обработчик пункта меню «👤 Мой профиль».

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
"""

import structlog
from aiogram import F, Router
from aiogram.types import Message

from src.bot.keyboards.main_menu import MENU_PROFILE
from src.bot.utils import escape_html
from src.services.user_service import UserService
from src.yclients.client import YClientsClient
from src.yclients.exceptions import YClientsError
from src.yclients.models import Client

log = structlog.get_logger("handlers.profile")

router = Router(name="profile")


@router.message(F.text == MENU_PROFILE)
async def show_profile(
    message: Message,
    user_service: UserService,
    yclients: YClientsClient,
) -> None:
    if message.from_user is None:
        return

    user = await user_service.find_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Похоже, ты не зарегистрирован. Отправь /start, и я тебя добавлю.")
        return

    if user.yclients_client_id is None:
        # Странный кейс — есть User в SQLite, но без привязки. Не должен
        # случаться при штатном пути, но обрабатываем.
        await message.answer(
            "Я тебя помню, но не вижу твою карточку в YClients. "
            "Напиши админу школы или сделай /start заново."
        )
        return

    try:
        client = await yclients.get_client_by_id(user.yclients_client_id)
    except YClientsError as exc:
        log.warning("profile.yclients_error", error=str(exc))
        await message.answer("Не получилось загрузить твой профиль из YClients. Попробуй позже.")
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
