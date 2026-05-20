"""Обработчик команды /start.

Логика:
- если пользователь уже есть в SQLite → главное меню;
- если нет → запускаем FSM регистрации, спрашиваем имя.

`state.clear()` в начале — на случай, если пользователь застрял в FSM
и отправляет /start, чтобы начать заново.
"""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from src.bot import texts
from src.bot.keyboards.main_menu import main_menu_kb
from src.bot.states.registration import RegistrationStates
from src.bot.utils import escape_html
from src.services.user_service import UserService

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    await state.clear()

    if message.from_user is None:
        await message.answer(texts.REG_NO_USER)
        return

    existing = await user_service.find_by_telegram_id(message.from_user.id)
    if existing is not None:
        name = existing.full_name or "друг"
        await message.answer(
            texts.START_WELCOME_REGISTERED.format(name=escape_html(name)),
            parse_mode="HTML",
            reply_markup=main_menu_kb(),
        )
        return

    await message.answer(
        texts.START_WELCOME_NEW,
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(RegistrationStates.waiting_for_name)
