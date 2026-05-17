"""Обработчики для «📅 Мои занятия» и отмены записи.

UX:
1. Кнопка «📅 Мои занятия» → бот тянет из YClients все записи клиента
   с date >= сегодня, фильтрует на «будущие» (datetime > now), показывает
   карточками. Под каждой карточкой — inline-кнопка «❌ Отменить» (если
   до начала больше CANCEL_HOURS_THRESHOLD часов).
2. Клик «❌ Отменить» → подтверждение «Да, отменить / Нет, оставить».
3. Клик «Да» → DELETE /records/{cid}/{record_id} → правим карточку на
   «Запись отменена», убираем кнопку.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards.bookings import (
    CANCEL_CONFIRM_PREFIX,
    CANCEL_DECLINE,
    CANCEL_PREFIX,
    cancel_button,
    cancel_confirm_keyboard,
)
from src.bot.keyboards.main_menu import MENU_MY_BOOKINGS
from src.services.user_service import UserService
from src.yclients.client import YClientsClient
from src.yclients.exceptions import YClientsError
from src.yclients.models import Record

log = structlog.get_logger("handlers.my_bookings")

router = Router(name="my_bookings")

# Сколько часов до начала занятия должно остаться, чтобы можно было отменить
# через бота. Если меньше — кнопку «Отменить» не показываем (политика школы).
CANCEL_HOURS_THRESHOLD = 24

# В Томске UTC+7 — таймзона записи в YClients.
TOMSK_TZ = timezone(timedelta(hours=7))


@router.message(F.text == MENU_MY_BOOKINGS)
async def show_my_bookings(
    message: Message,
    user_service: UserService,
    yclients: YClientsClient,
) -> None:
    if message.from_user is None:
        return

    user = await user_service.find_by_telegram_id(message.from_user.id)
    if user is None or user.yclients_client_id is None:
        await message.answer("Похоже, ты не зарегистрирован. Отправь /start, и я тебя добавлю.")
        return

    # YClients принимает start_date/end_date, но возвращает в т.ч. сегодняшние
    # записи, у которых время уже прошло. Доп. фильтр делаем на клиенте.
    now = datetime.now(tz=TOMSK_TZ)
    today = now.date().isoformat()
    horizon = (now + timedelta(days=60)).date().isoformat()

    try:
        records = await yclients.get_client_records(
            client_id=user.yclients_client_id,
            start_date=today,
            end_date=horizon,
        )
    except YClientsError as exc:
        log.warning("my_bookings.yclients_error", error=str(exc))
        await message.answer("Не получилось загрузить занятия из YClients. Попробуй позже.")
        return

    future = [r for r in records if _is_future(r, now)]

    if not future:
        await message.answer(
            "📅 На ближайшие 2 месяца записей нет.\n\n"
            "Запиши себя через «🥁 Записаться» (скоро будет работать)."
        )
        return

    # YClients возвращает записи свежими сверху, нам же удобнее по возрастанию.
    future.sort(key=lambda r: r.datetime or r.date or "")

    await message.answer(f"📅 У тебя {len(future)} ближайших занятий:")
    for record in future:
        text = _format_record(record)
        hours_left = _hours_until(record, now)
        if hours_left is None or hours_left >= CANCEL_HOURS_THRESHOLD:
            kb = cancel_button(record.id)
            await message.answer(text, parse_mode="HTML", reply_markup=kb)
        else:
            text += (
                f"\n\n<i>До начала меньше {CANCEL_HOURS_THRESHOLD} ч — "
                "отмена через бота недоступна. Позвони в школу.</i>"
            )
            await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith(f"{CANCEL_PREFIX}:"))
async def confirm_cancel(callback: CallbackQuery) -> None:
    """Первый клик «Отменить» → подтверждение."""
    if callback.data is None:
        await callback.answer()
        return
    record_id = int(callback.data.split(":", 1)[1])
    await callback.message.edit_reply_markup(reply_markup=cancel_confirm_keyboard(record_id))
    await callback.answer("Точно отменить?")


@router.callback_query(F.data == CANCEL_DECLINE)
async def cancel_declined(callback: CallbackQuery) -> None:
    """«Нет, оставить» → возвращаем исходную кнопку «Отменить»."""
    # Парсим record_id из текста сообщения — у нас нет в callback_data;
    # проще снова достать его из исходного «Отменить»-кейлборда не получится
    # после редактирования. Поэтому просто убираем все кнопки.
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Окей, оставил запись")


@router.callback_query(F.data.startswith(f"{CANCEL_CONFIRM_PREFIX}:"))
async def do_cancel(
    callback: CallbackQuery,
    yclients: YClientsClient,
) -> None:
    """«Да, отменить» → реально дёргаем YClients."""
    if callback.data is None:
        await callback.answer()
        return
    record_id = int(callback.data.split(":", 1)[1])

    try:
        await yclients.cancel_record(record_id)
    except YClientsError as exc:
        log.warning("cancel.yclients_error", record_id=record_id, error=str(exc))
        await callback.answer("Не получилось отменить. Попробуй позже.", show_alert=True)
        return

    try:
        await callback.message.edit_text(
            (callback.message.html_text or callback.message.text or "")
            + "\n\n<b>❌ Запись отменена.</b>",
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        # Если сообщение нельзя редактировать (старое, например) — отправим новое.
        await callback.message.answer("Запись отменена.")

    await callback.answer("Отменено")


def _format_record(r: Record) -> str:
    """Карточка занятия в HTML."""
    when = _format_datetime(r)
    services = ", ".join(s.title for s in r.services) or "Занятие"
    staff = r.staff.name if r.staff else "Любой тренер"
    return f"🥁 <b>{_escape(services)}</b>\n👤 {_escape(staff)}\n🕐 {when}"


def _format_datetime(r: Record) -> str:
    """Берём datetime (с tz) если есть, иначе date. Печатаем в локальной TZ Томска."""
    if r.datetime:
        try:
            dt = datetime.fromisoformat(r.datetime)
            return dt.astimezone(TOMSK_TZ).strftime("%d.%m.%Y, %H:%M")
        except ValueError:
            pass
    return r.date or "время не указано"


def _is_future(r: Record, now: datetime) -> bool:
    """True, если занятие ещё впереди."""
    if not r.datetime:
        return True  # без datetime не можем точно сказать — показываем
    try:
        dt = datetime.fromisoformat(r.datetime)
    except ValueError:
        return True
    return dt > now


def _hours_until(r: Record, now: datetime) -> float | None:
    """Часов до начала занятия. None, если datetime распарсить не получилось."""
    if not r.datetime:
        return None
    try:
        dt = datetime.fromisoformat(r.datetime)
    except ValueError:
        return None
    return (dt - now).total_seconds() / 3600


def _escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
