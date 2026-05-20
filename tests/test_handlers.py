"""Unit-тесты обработчиков бота.

Подход: вызываем handler-функцию напрямую, передавая моки на Message/FSMContext/
UserService. Не поднимаем aiogram Dispatcher и не симулируем сетевую часть —
это исключительно про логику ветвления.

Это даёт быструю обратную связь, но НЕ покрывает:
- правильность регистрации в Router (фильтры F.text, состояния FSM);
- порядок роутеров в main.py;
- сериализацию ответов в Telegram.
Эти вещи проверяются интеграционно (Никита через @DrumFamily_Tomsk_Bot).
"""

from unittest.mock import AsyncMock, MagicMock

from aiogram.fsm.state import State

from src.bot import texts
from src.bot.handlers.booking import (
    booking_unrecognized,
    cancel_booking,
    picked_service,
    picked_slot,
    start_booking,
)
from src.bot.handlers.commands import cmd_cancel, cmd_help
from src.bot.handlers.menu_stub import LEGACY_ABOUT, fallback
from src.bot.handlers.my_bookings import show_my_bookings
from src.bot.handlers.profile import show_profile
from src.bot.handlers.registration import (
    got_contact,
    got_name,
    got_phone_text,
    name_not_text,
    phone_not_recognized,
)
from src.bot.handlers.start import cmd_start
from src.bot.handlers.static_info import (
    show_admin,
    show_contacts,
    show_faq,
    show_prices,
)
from src.bot.states.booking import BookingStates
from src.bot.states.registration import RegistrationStates
from src.db.models import User
from src.yclients.exceptions import YClientsServerError
from src.yclients.models import Client as YClient
from src.yclients.models import Record, Service, Staff

# ---------- хелперы ----------


def make_message(*, text: str | None = None, contact_phone: str | None = None) -> MagicMock:
    """Собирает MagicMock(Message) с from_user, text и опциональным contact."""
    msg = MagicMock()
    msg.from_user = MagicMock(id=12345, full_name="Тест Тестов")
    msg.text = text
    msg.answer = AsyncMock()
    if contact_phone is not None:
        msg.contact = MagicMock(phone_number=contact_phone)
    else:
        msg.contact = None
    return msg


def make_state(current: State | None = None) -> AsyncMock:
    """Собирает AsyncMock(FSMContext) с настраиваемым get_state."""
    state = AsyncMock()
    state.get_state.return_value = current.state if current else None
    state.get_data.return_value = {}
    return state


# ---------- /start ----------


async def test_start_for_registered_user_shows_main_menu() -> None:
    """Зарегистрированный → главное меню, без FSM."""
    message = make_message(text="/start")
    state = make_state()
    user_service = AsyncMock()
    user_service.find_by_telegram_id.return_value = User(
        telegram_id=12345, full_name="Иван", yclients_client_id=42
    )

    await cmd_start(message, state, user_service)

    user_service.find_by_telegram_id.assert_awaited_once_with(12345)
    state.clear.assert_awaited_once()
    state.set_state.assert_not_called()
    message.answer.assert_awaited_once()
    # имя из БД попало в текст приветствия
    args, kwargs = message.answer.call_args
    assert "Иван" in args[0]


async def test_start_for_new_user_starts_fsm() -> None:
    """Новый пользователь → set_state(waiting_for_name)."""
    message = make_message(text="/start")
    state = make_state()
    user_service = AsyncMock()
    user_service.find_by_telegram_id.return_value = None

    await cmd_start(message, state, user_service)

    state.clear.assert_awaited_once()
    state.set_state.assert_awaited_once_with(RegistrationStates.waiting_for_name)
    message.answer.assert_awaited_once()


# ---------- FSM регистрации ----------


async def test_got_name_short_name_stays_in_state() -> None:
    """Имя короче 2 символов → переспрашиваем, состояние не меняется."""
    message = make_message(text="A")
    state = make_state(RegistrationStates.waiting_for_name)

    await got_name(message, state)

    state.update_data.assert_not_called()
    state.set_state.assert_not_called()
    message.answer.assert_awaited_once()


async def test_got_name_normal_advances_to_phone() -> None:
    message = make_message(text="Иван")
    state = make_state(RegistrationStates.waiting_for_name)

    await got_name(message, state)

    state.update_data.assert_awaited_once_with(name="Иван")
    state.set_state.assert_awaited_once_with(RegistrationStates.waiting_for_phone)


async def test_got_name_strips_whitespace() -> None:
    message = make_message(text="  Иван  ")
    state = make_state(RegistrationStates.waiting_for_name)

    await got_name(message, state)

    state.update_data.assert_awaited_once_with(name="Иван")


async def test_got_phone_text_garbage_keeps_state() -> None:
    """Невалидный телефон → переспрашиваем, register не дёргается."""
    message = make_message(text="фигня")
    state = make_state(RegistrationStates.waiting_for_phone)
    state.get_data.return_value = {"name": "Иван"}
    user_service = AsyncMock()

    await got_phone_text(message, state, user_service)

    user_service.register.assert_not_called()
    state.clear.assert_not_called()


async def test_got_phone_text_valid_calls_register() -> None:
    message = make_message(text="+7 999 111 22 33")
    state = make_state(RegistrationStates.waiting_for_phone)
    state.get_data.return_value = {"name": "Иван"}
    user_service = AsyncMock()
    user_service.register.return_value = User(
        telegram_id=12345, full_name="Иван", phone="+79991112233", yclients_client_id=42
    )

    await got_phone_text(message, state, user_service)

    user_service.register.assert_awaited_once_with(
        telegram_id=12345, name="Иван", phone="+79991112233"
    )
    state.clear.assert_awaited_once()


async def test_got_contact_uses_contact_phone() -> None:
    message = make_message(contact_phone="79991112233")
    state = make_state(RegistrationStates.waiting_for_phone)
    state.get_data.return_value = {"name": "Иван"}
    user_service = AsyncMock()
    user_service.register.return_value = User(
        telegram_id=12345, yclients_client_id=42, full_name="Иван", phone="+79991112233"
    )

    await got_contact(message, state, user_service)

    user_service.register.assert_awaited_once()
    _, kwargs = user_service.register.call_args
    assert kwargs["phone"] == "+79991112233"


async def test_got_phone_without_name_in_state_resets() -> None:
    """Если name в state потерялся (странный сценарий) — отправляем заново на /start."""
    message = make_message(text="+79991112233")
    state = make_state(RegistrationStates.waiting_for_phone)
    state.get_data.return_value = {}  # нет имени
    user_service = AsyncMock()

    await got_phone_text(message, state, user_service)

    user_service.register.assert_not_called()
    state.clear.assert_awaited_once()


# ---------- FSM catch-all (не-текстовые сообщения) ----------


async def test_name_not_text_handler_replies() -> None:
    """Стикер на шаге waiting_for_name → подсказка."""
    message = make_message()  # без text и contact — имитирует стикер/фото

    await name_not_text(message)

    message.answer.assert_awaited_once()


async def test_phone_not_recognized_handler_replies() -> None:
    message = make_message()

    await phone_not_recognized(message)

    message.answer.assert_awaited_once()


# ---------- сервисные команды ----------


async def test_cancel_with_active_state_returns_to_menu_for_registered() -> None:
    message = make_message(text="/cancel")
    state = make_state(RegistrationStates.waiting_for_name)
    user_service = AsyncMock()
    user_service.find_by_telegram_id.return_value = User(
        telegram_id=12345, full_name="Иван", yclients_client_id=42
    )

    await cmd_cancel(message, state, user_service)

    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once()


async def test_cancel_without_state_does_nothing() -> None:
    message = make_message(text="/cancel")
    state = make_state(current=None)
    user_service = AsyncMock()

    await cmd_cancel(message, state, user_service)

    state.clear.assert_awaited_once()  # clear всё равно вызывается — идемпотентно
    user_service.find_by_telegram_id.assert_not_called()
    message.answer.assert_awaited_once()
    args, _ = message.answer.call_args
    assert "не в середине" in args[0].lower() or "нечего" in args[0].lower()


async def test_help_replies_with_commands_overview() -> None:
    message = make_message(text="/help")

    await cmd_help(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.call_args
    assert "/start" in args[0]
    assert "/cancel" in args[0]


# ---------- static_info: контакты, цены, FAQ, админ ----------


async def test_contacts_replies_with_static_text() -> None:
    message = make_message(text="📍 Адрес")
    await show_contacts(message)
    message.answer.assert_awaited_once()
    text = message.answer.call_args.args[0]
    assert "Drum Family" in text
    assert "Комсомольский" in text


async def test_prices_replies() -> None:
    message = make_message(text="💳 Стоимость")
    await show_prices(message)
    message.answer.assert_awaited_once()
    assert "Стоимость" in message.answer.call_args.args[0]


async def test_faq_replies() -> None:
    message = make_message(text="❓ Частые вопросы")
    await show_faq(message)
    message.answer.assert_awaited_once()
    assert "Частые вопросы" in message.answer.call_args.args[0]


async def test_admin_replies() -> None:
    message = make_message(text="💬 Написать админу")
    await show_admin(message)
    message.answer.assert_awaited_once()
    assert "@Drum_Family_admin" in message.answer.call_args.args[0]


# ---------- menu_stub: fallback на неизвестные сообщения ----------


async def test_fallback_legacy_about_button() -> None:
    """Если кто-то нажмёт сохранённую кнопку «ℹ️ О школе» из старого
    меню — выдаём ABOUT_TEXT, а не unknown-command."""
    message = make_message(text=LEGACY_ABOUT)
    await fallback(message)
    message.answer.assert_awaited_once_with(texts.ABOUT_TEXT, parse_mode="HTML")


async def test_fallback_unknown_text() -> None:
    """На произвольный мусорный текст — UNKNOWN_COMMAND."""
    message = make_message(text="какая-то ерунда")
    await fallback(message)
    message.answer.assert_awaited_once_with(texts.UNKNOWN_COMMAND)


# ---------- profile ----------


async def test_profile_shows_yclients_data() -> None:
    message = make_message(text="👤 Мой профиль")
    user_service = AsyncMock()
    user_service.find_by_telegram_id.return_value = User(
        telegram_id=12345, full_name="Никита", yclients_client_id=285529314
    )
    yclients = AsyncMock()
    yclients.get_client_by_id.return_value = YClient(
        id=285529314,
        name="Никита",
        surname="Макаров",
        display_name="Никита Макаров",
        phone="+79991112233",
        email="n@example.com",
        visits=38,
        balance=-3500,
        spent=112350,
        paid=108850,
    )

    await show_profile(message, user_service, yclients)

    yclients.get_client_by_id.assert_awaited_once_with(285529314)
    message.answer.assert_awaited_once()
    text = message.answer.call_args.args[0]
    assert "Никита Макаров" in text
    assert "38" in text
    assert "-3500" in text or "−3500" in text or "−3 500" in text or "-3 500" in text


async def test_profile_when_user_not_registered() -> None:
    message = make_message(text="👤 Мой профиль")
    user_service = AsyncMock()
    user_service.find_by_telegram_id.return_value = None
    yclients = AsyncMock()

    await show_profile(message, user_service, yclients)

    yclients.get_client_by_id.assert_not_called()
    message.answer.assert_awaited_once()
    assert "/start" in message.answer.call_args.args[0]


async def test_profile_when_yclients_fails() -> None:
    message = make_message(text="👤 Мой профиль")
    user_service = AsyncMock()
    user_service.find_by_telegram_id.return_value = User(telegram_id=12345, yclients_client_id=999)
    yclients = AsyncMock()
    yclients.get_client_by_id.side_effect = YClientsServerError("YClients down")

    await show_profile(message, user_service, yclients)

    message.answer.assert_awaited_once()
    assert "позже" in message.answer.call_args.args[0].lower()


# ---------- my bookings ----------


def _record(record_id: int, datetime_iso: str, service_title: str = "Тренировка") -> Record:
    return Record(
        id=record_id,
        datetime=datetime_iso,
        date=datetime_iso.split("T")[0] + " " + datetime_iso.split("T")[1][:8],
        seance_length=3600,
        services=[Service(id=1, title=service_title)],
        staff=Staff(id=10, name="Влад"),
        visit_attendance=0,
    )


async def test_my_bookings_when_empty() -> None:
    message = make_message(text="📅 Мои занятия")
    user_service = AsyncMock()
    user_service.find_by_telegram_id.return_value = User(telegram_id=12345, yclients_client_id=999)
    yclients = AsyncMock()
    yclients.get_client_records.return_value = []

    await show_my_bookings(message, user_service, yclients)

    # Одно сообщение «занятий нет», без карточек.
    assert message.answer.await_count == 1
    assert "нет" in message.answer.call_args.args[0].lower()


async def test_my_bookings_filters_past_records() -> None:
    """Записи с datetime в прошлом не показываем."""
    message = make_message(text="📅 Мои занятия")
    user_service = AsyncMock()
    user_service.find_by_telegram_id.return_value = User(telegram_id=12345, yclients_client_id=999)
    yclients = AsyncMock()
    yclients.get_client_records.return_value = [
        _record(100, "2020-01-01T10:00:00+07:00"),  # давно прошло
        _record(200, "2099-01-01T10:00:00+07:00"),  # точно в будущем
    ]

    await show_my_bookings(message, user_service, yclients)

    # Должно быть: 1 «у тебя N занятий» + 1 карточка для будущей записи.
    assert message.answer.await_count == 2
    summary = message.answer.await_args_list[0].args[0]
    assert "1" in summary  # одно занятие осталось после фильтрации


async def test_my_bookings_when_user_not_registered() -> None:
    message = make_message(text="📅 Мои занятия")
    user_service = AsyncMock()
    user_service.find_by_telegram_id.return_value = None
    yclients = AsyncMock()

    await show_my_bookings(message, user_service, yclients)

    yclients.get_client_records.assert_not_called()
    message.answer.assert_awaited_once()
    assert "/start" in message.answer.call_args.args[0]


# ---------- booking FSM ----------


def make_callback(*, data: str | None = None) -> MagicMock:
    """Mock CallbackQuery с from_user, data, message, answer."""
    cb = MagicMock()
    cb.from_user = MagicMock(id=12345)
    cb.data = data
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.message.edit_reply_markup = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.answer = AsyncMock()
    return cb


async def test_start_booking_for_new_user_redirects_to_registration() -> None:
    message = make_message(text="🥁 Записаться")
    state = make_state()
    user_service = AsyncMock()
    user_service.find_by_telegram_id.return_value = None
    yclients = AsyncMock()

    await start_booking(message, state, user_service, yclients)

    yclients.get_services.assert_not_called()
    state.set_state.assert_not_called()
    message.answer.assert_awaited_once()
    assert "/start" in message.answer.call_args.args[0]


async def test_start_booking_for_registered_user_sets_state_and_caches_services() -> None:
    message = make_message(text="🥁 Записаться")
    state = make_state()
    user_service = AsyncMock()
    user_service.find_by_telegram_id.return_value = User(telegram_id=12345, yclients_client_id=42)
    yclients = AsyncMock()
    yclients.get_services.return_value = [
        Service(id=111, title="Услуга один"),
        Service(id=222, title="Услуга два"),
    ]

    await start_booking(message, state, user_service, yclients)

    state.clear.assert_awaited_once()  # очистили любой предыдущий FSM
    state.set_state.assert_awaited_once_with(BookingStates.choosing_service)
    # Кэш услуг положен в FSM data — пригодится в picked_service
    state.update_data.assert_awaited_once_with(
        services_cache={111: "Услуга один", 222: "Услуга два"}
    )
    message.answer.assert_awaited_once()


async def test_picked_service_uses_cache_and_advances_to_staff() -> None:
    """Не должен повторно вызывать get_services — берёт название из кэша."""
    callback = make_callback(data="bk_svc:111")
    state = make_state(BookingStates.choosing_service)
    state.get_data.return_value = {"services_cache": {111: "Услуга один"}}
    yclients = AsyncMock()
    yclients.get_staff.return_value = [Staff(id=10, name="Влад")]

    await picked_service(callback, state, yclients)

    # services НЕ дёргаем — это и есть смысл #6 (кэш)
    yclients.get_services.assert_not_called()
    yclients.get_staff.assert_awaited_once_with(service_ids=[111])
    state.set_state.assert_awaited_once_with(BookingStates.choosing_staff)
    # service_id и staff_cache попали в FSM data
    call = state.update_data.await_args_list[0]
    assert call.kwargs["service_id"] == 111
    assert call.kwargs["service_title"] == "Услуга один"
    assert call.kwargs["staff_cache"] == {10: "Влад"}


async def test_picked_service_unknown_id_aborts() -> None:
    """Если callback пришёл с устаревшим service_id (нет в кэше) — выходим."""
    callback = make_callback(data="bk_svc:999")
    state = make_state(BookingStates.choosing_service)
    state.get_data.return_value = {"services_cache": {111: "Старая услуга"}}
    yclients = AsyncMock()

    await picked_service(callback, state, yclients)

    yclients.get_staff.assert_not_called()
    state.clear.assert_awaited_once()
    callback.answer.assert_awaited_once()


async def test_picked_slot_shows_summary() -> None:
    callback = make_callback(data="bk_sl:2099-05-20T10:00:00+07:00")
    state = make_state(BookingStates.choosing_slot)
    state.get_data.return_value = {
        "service_title": "Персональная",
        "staff_name": "Влад",
    }

    await picked_slot(callback, state)

    state.set_state.assert_awaited_once_with(BookingStates.confirming)
    state.update_data.assert_awaited_once_with(slot_datetime="2099-05-20T10:00:00+07:00")
    callback.message.edit_text.assert_awaited_once()
    text = callback.message.edit_text.call_args.args[0]
    assert "Персональная" in text
    assert "Влад" in text
    assert "20.05.2099" in text  # отформатированная дата
    assert "10:00" in text


async def test_cancel_booking_clears_state_and_shows_menu() -> None:
    callback = make_callback(data="bk_cancel")
    state = make_state(BookingStates.choosing_service)

    await cancel_booking(callback, state)

    state.clear.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once()
    # после отмены отправляется новое сообщение «Что дальше?» с main_menu_kb
    callback.message.answer.assert_awaited_once()


async def test_booking_unrecognized_replies_with_hint() -> None:
    """В любом состоянии FSM на не-кнопочное сообщение — подсказка."""
    message = make_message(text="произвольный текст")

    await booking_unrecognized(message)

    message.answer.assert_awaited_once()
    assert "/cancel" in message.answer.call_args.args[0]
