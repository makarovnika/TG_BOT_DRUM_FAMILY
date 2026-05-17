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

import pytest
from aiogram.fsm.state import State

from src.bot.handlers.commands import cmd_cancel, cmd_help
from src.bot.handlers.menu_stub import ABOUT_TEXT, about, stub
from src.bot.handlers.registration import (
    got_contact,
    got_name,
    got_phone_text,
    name_not_text,
    phone_not_recognized,
)
from src.bot.handlers.start import cmd_start
from src.bot.keyboards.main_menu import MENU_BOOK, MENU_MY_BOOKINGS, MENU_PROFILE
from src.bot.states.registration import RegistrationStates
from src.db.models import User

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


# ---------- menu stubs ----------


async def test_about_replies_with_static_text() -> None:
    message = make_message(text="ℹ️ О школе")

    await about(message)

    message.answer.assert_awaited_once_with(ABOUT_TEXT)


@pytest.mark.parametrize("button", [MENU_BOOK, MENU_MY_BOOKINGS, MENU_PROFILE])
async def test_menu_stub_replies(button: str) -> None:
    message = make_message(text=button)

    await stub(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.call_args
    assert "🚧" in args[0] or "готовится" in args[0].lower()
