"""FSM записи на индивидуальное занятие.

Шаги:
1. Кнопка «🥁 Записаться» → choosing_service.
   Бот тянет get_services(), показывает inline-список.
2. Клик service:N → choosing_staff.
   Бот тянет get_staff(service_ids=[N]) (только релевантные тренеры), показывает.
3. Клик staff:M → choosing_date.
   Бот тянет get_book_dates(staff_id=M, service_ids=[N], 14 дней вперёд).
4. Клик date:YYYY-MM-DD → choosing_slot.
   Бот тянет get_book_times(staff_id=M, date, service_ids=[N]).
5. Клик slot:ISO_DT → confirming.
   Бот показывает summary с кнопками «✅ Записаться» / «↩️ Отмена».
6. Клик confirm:yes → book_record(...).
   Если YClients требует SMS-подтверждение — это не покрыто, увидим
   при первой реальной записи (открытый вопрос).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot import texts
from src.bot.assets import banner, remember_banner
from src.bot.keyboards.booking import (
    CANCEL_DATA,
    CONFIRM_PREFIX,
    DATE_PREFIX,
    SERVICE_PREFIX,
    SLOT_PREFIX,
    STAFF_PREFIX,
    confirm_keyboard,
    dates_keyboard,
    post_booking_keyboard,
    services_keyboard,
    slots_keyboard,
    staff_keyboard,
)
from src.bot.keyboards.main_menu import MENU_BOOK, main_menu_kb
from src.bot.states.booking import BookingStates
from src.bot.utils import escape_html
from src.services.user_service import UserService
from src.yclients.client import YClientsClient
from src.yclients.exceptions import YClientsError
from src.yclients.models import BookRecordAppointment

log = structlog.get_logger("handlers.booking")

router = Router(name="booking")

TOMSK_TZ = timezone(timedelta(hours=7))
BOOK_HORIZON_DAYS = 14


@router.message(F.text == MENU_BOOK)
async def start_booking(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    yclients: YClientsClient,
) -> None:
    """Точка входа FSM записи.

    Тянем услуги один раз, кладём в FSM-data `{id: title}` — на следующих
    шагах не нужно повторно дёргать /book_services.
    """
    if message.from_user is None:
        return

    user = await user_service.find_by_telegram_id(message.from_user.id)
    if user is None or user.yclients_client_id is None:
        await message.answer(texts.BOOKING_NEED_REGISTRATION)
        return

    await state.clear()

    try:
        services = await yclients.get_services()
    except YClientsError as exc:
        log.warning("booking.services_error", error=str(exc))
        await message.answer(texts.BOOKING_SERVICES_ERROR)
        return

    if not services:
        await message.answer(texts.BOOKING_NO_SERVICES)
        return

    await state.set_state(BookingStates.choosing_service)
    # Кэшируем `{id: title}` в FSM-data — на следующих шагах достанем без API.
    await state.update_data(services_cache={s.id: s.title for s in services})
    # Баннер «Прокачай себя!» — только на входе в FSM. Дальше едитим уже без
    # фото, потому что aiogram не позволяет менять photo через edit_text.
    sent = await message.answer_photo(
        photo=banner("trial"),
        caption=texts.BOOKING_ASK_SERVICE,
        reply_markup=services_keyboard([(s.id, s.title) for s in services]),
    )
    remember_banner("trial", sent)


@router.callback_query(BookingStates.choosing_service, F.data.startswith(f"{SERVICE_PREFIX}:"))
async def picked_service(
    callback: CallbackQuery,
    state: FSMContext,
    yclients: YClientsClient,
) -> None:
    if callback.data is None or callback.message is None:
        await callback.answer()
        return
    service_id = int(callback.data.split(":", 1)[1])

    data = await state.get_data()
    services_cache: dict[int, str] = {int(k): v for k, v in data.get("services_cache", {}).items()}
    service_title = services_cache.get(service_id)
    if service_title is None:
        await callback.answer(texts.BOOKING_SERVICE_LOST, show_alert=True)
        await state.clear()
        return

    try:
        staff = await yclients.get_staff(service_ids=[service_id])
    except YClientsError as exc:
        log.warning("booking.staff_error", error=str(exc))
        await callback.answer(texts.BOOKING_STAFF_ERROR, show_alert=True)
        await state.clear()
        return

    if not staff:
        await callback.message.edit_caption(caption=texts.BOOKING_NO_STAFF)
        await state.clear()
        await callback.answer()
        return

    await state.update_data(
        service_id=service_id,
        service_title=service_title,
        staff_cache={m.id: m.name for m in staff},
    )
    await state.set_state(BookingStates.choosing_staff)
    # edit_caption, не edit_text — потому что сообщение это photo (см. start_booking).
    await callback.message.edit_caption(
        caption=texts.BOOKING_ASK_STAFF.format(service=escape_html(service_title)),
        parse_mode="HTML",
        reply_markup=staff_keyboard([(m.id, m.name) for m in staff]),
    )
    await callback.answer()


@router.callback_query(BookingStates.choosing_staff, F.data.startswith(f"{STAFF_PREFIX}:"))
async def picked_staff(
    callback: CallbackQuery,
    state: FSMContext,
    yclients: YClientsClient,
) -> None:
    if callback.data is None or callback.message is None:
        await callback.answer()
        return
    staff_id = int(callback.data.split(":", 1)[1])
    data = await state.get_data()
    service_id = data["service_id"]
    staff_cache: dict[int, str] = {int(k): v for k, v in data.get("staff_cache", {}).items()}
    staff_name = staff_cache.get(staff_id)
    if staff_name is None:
        await callback.answer(texts.BOOKING_STAFF_LOST, show_alert=True)
        await state.clear()
        return

    today = datetime.now(tz=TOMSK_TZ).date()
    horizon = today + timedelta(days=BOOK_HORIZON_DAYS)
    try:
        dates = await yclients.get_book_dates(
            staff_id=staff_id,
            service_ids=[service_id],
            date_from=today.isoformat(),
            date_to=horizon.isoformat(),
        )
    except YClientsError as exc:
        log.warning("booking.dates_error", error=str(exc))
        await callback.answer(texts.BOOKING_DATES_ERROR, show_alert=True)
        await state.clear()
        return

    if not dates.booking_dates:
        await callback.message.edit_caption(
            caption=texts.BOOKING_NO_DATES.format(
                service=escape_html(data["service_title"]),
                staff=escape_html(staff_name),
                days=BOOK_HORIZON_DAYS,
            ),
            parse_mode="HTML",
        )
        await state.clear()
        await callback.answer()
        return

    await state.update_data(staff_id=staff_id, staff_name=staff_name)
    await state.set_state(BookingStates.choosing_date)
    await callback.message.edit_caption(
        caption=texts.BOOKING_ASK_DATE.format(
            service=escape_html(data["service_title"]),
            staff=escape_html(staff_name),
        ),
        parse_mode="HTML",
        reply_markup=dates_keyboard(dates.booking_dates),
    )
    await callback.answer()


@router.callback_query(BookingStates.choosing_date, F.data.startswith(f"{DATE_PREFIX}:"))
async def picked_date(
    callback: CallbackQuery,
    state: FSMContext,
    yclients: YClientsClient,
) -> None:
    if callback.data is None or callback.message is None:
        await callback.answer()
        return
    date_iso = callback.data.split(":", 1)[1]
    data = await state.get_data()
    service_id = data["service_id"]
    staff_id = data["staff_id"]

    try:
        slots = await yclients.get_book_times(
            staff_id=staff_id,
            date=date_iso,
            service_ids=[service_id],
        )
    except YClientsError as exc:
        log.warning("booking.slots_error", error=str(exc))
        await callback.answer(texts.BOOKING_SLOTS_ERROR, show_alert=True)
        await state.clear()
        return

    if not slots:
        await callback.answer(texts.BOOKING_NO_SLOTS, show_alert=True)
        return

    await state.update_data(date=date_iso)
    await state.set_state(BookingStates.choosing_slot)

    slot_pairs = [(s.time or "—", s.datetime or "") for s in slots if s.datetime]

    await callback.message.edit_caption(
        caption=texts.BOOKING_ASK_TIME.format(
            service=escape_html(data["service_title"]),
            staff=escape_html(data["staff_name"]),
            date=date_iso,
        ),
        parse_mode="HTML",
        reply_markup=slots_keyboard(slot_pairs),
    )
    await callback.answer()


@router.callback_query(BookingStates.choosing_slot, F.data.startswith(f"{SLOT_PREFIX}:"))
async def picked_slot(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.message is None:
        await callback.answer()
        return
    slot_iso = callback.data.split(":", 1)[1]
    data = await state.get_data()

    await state.update_data(slot_datetime=slot_iso)
    await state.set_state(BookingStates.confirming)

    pretty_time = _format_iso(slot_iso)

    await callback.message.edit_caption(
        caption=texts.BOOKING_CONFIRM.format(
            service=escape_html(data["service_title"]),
            staff=escape_html(data["staff_name"]),
            when=pretty_time,
        ),
        parse_mode="HTML",
        reply_markup=confirm_keyboard(),
    )
    await callback.answer()


@router.callback_query(BookingStates.confirming, F.data == f"{CONFIRM_PREFIX}:yes")
async def confirm_booking(
    callback: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
    yclients: YClientsClient,
) -> None:
    if callback.message is None or callback.from_user is None:
        await callback.answer()
        return
    data = await state.get_data()

    user = await user_service.find_by_telegram_id(callback.from_user.id)
    if user is None or user.full_name is None or user.phone is None:
        await callback.answer(texts.BOOKING_PROFILE_INCOMPLETE, show_alert=True)
        await state.clear()
        return

    # YClients школы Drum Family требует email при создании записи (422
    # «Не передан обязательный параметр email»). В нашей SQLite email
    # не хранится, поэтому тянем актуальный из YClients-карточки клиента.
    # Если в YClients email тоже не заполнен — попросим админа добавить.
    if user.yclients_client_id is None:
        await callback.answer(texts.BOOKING_NOT_LINKED, show_alert=True)
        await state.clear()
        return
    try:
        yc_client = await yclients.get_client_by_id(user.yclients_client_id)
    except YClientsError as exc:
        log.warning("booking.get_client_error", error=str(exc))
        await callback.message.edit_caption(caption=texts.BOOKING_CLIENT_FETCH_ERROR)
        await state.clear()
        await callback.answer()
        return

    if not yc_client.email:
        await callback.message.edit_caption(caption=texts.BOOKING_EMAIL_REQUIRED, parse_mode="HTML")
        await state.clear()
        await callback.answer()
        return

    appointment = BookRecordAppointment(
        id=1,
        services=[data["service_id"]],
        staff_id=data["staff_id"],
        datetime=data["slot_datetime"],
    )

    try:
        result = await yclients.book_record(
            phone=user.phone,
            fullname=user.full_name,
            email=yc_client.email,
            appointments=[appointment],
        )
    except YClientsError as exc:
        log.warning("booking.book_error", error=str(exc))
        # 422 «уже занято», SMS-required и т. п. — показываем человекочитаемо.
        await callback.message.edit_caption(
            caption=texts.BOOKING_FAILED.format(error=escape_html(str(exc))),
            parse_mode="HTML",
        )
        await state.clear()
        await callback.answer()
        return

    record_id = result[0].id if result else None
    log.info("booking.created", record_id=record_id, telegram_id=user.telegram_id)

    pretty_time = _format_iso(data["slot_datetime"])
    # ТЗ §9.5: под подтверждением — inline-кнопки «Отменить» и «Маршрут».
    # Если по какой-то причине record_id не пришёл (странный кейс) — даём
    # сообщение без кнопок, чтобы не сломалось.
    post_kb = post_booking_keyboard(record_id) if record_id else None
    await callback.message.edit_caption(
        caption=texts.BOOKING_SUCCESS.format(
            service=escape_html(data["service_title"]),
            staff=escape_html(data["staff_name"]),
            when=pretty_time,
        ),
        parse_mode="HTML",
        reply_markup=post_kb,
    )
    await state.clear()
    await callback.answer(texts.TOAST_BOOKING_DONE)
    # Возвращаем главное меню следующим сообщением
    await callback.message.answer(texts.BOOKING_WHAT_NEXT, reply_markup=main_menu_kb())


@router.callback_query(F.data == CANCEL_DATA)
async def cancel_booking(callback: CallbackQuery, state: FSMContext) -> None:
    """Кнопка «Отмена» на любом шаге FSM."""
    if callback.message is None:
        await callback.answer()
        return
    await state.clear()
    await callback.message.edit_caption(caption=texts.BOOKING_CANCELLED)
    await callback.message.answer(texts.BOOKING_WHAT_NEXT, reply_markup=main_menu_kb())
    await callback.answer()


# Catch-all для текстовых сообщений внутри FSM записи — чтобы пользователь
# не «застревал», если случайно напишет что-то вместо нажатия кнопки.
# Регистрируем ПОСЛЕ всех callback_query-handler'ов на эти же состояния.


@router.message(BookingStates.choosing_service)
@router.message(BookingStates.choosing_staff)
@router.message(BookingStates.choosing_date)
@router.message(BookingStates.choosing_slot)
@router.message(BookingStates.confirming)
async def booking_unrecognized(message: Message) -> None:
    await message.answer(texts.BOOKING_UNRECOGNIZED)


def _format_iso(iso: str) -> str:
    """ISO с tz → 'DD.MM.YYYY, HH:MM' в локальной TZ Томска."""
    try:
        dt = datetime.fromisoformat(iso)
        return dt.astimezone(TOMSK_TZ).strftime("%d.%m.%Y, %H:%M")
    except ValueError:
        return iso
