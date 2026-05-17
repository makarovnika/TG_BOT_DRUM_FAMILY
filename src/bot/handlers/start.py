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

from src.bot.keyboards.main_menu import main_menu_kb
from src.bot.states.registration import RegistrationStates
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
        # На всякий случай — теоретически в Telegram такого не бывает.
        await message.answer("Не получилось определить тебя как пользователя Telegram.")
        return

    existing = await user_service.find_by_telegram_id(message.from_user.id)
    if existing is not None:
        name = existing.full_name or "друг"
        await message.answer(
            f"С возвращением, {name}! 🥁\nВыбери, что хочешь сделать.",
            reply_markup=main_menu_kb(),
        )
        return

    await message.answer(
        "Привет! Я бот школы барабанов Drum Family Томск. 🥁\n\n"
        "Давай знакомиться — как тебя зовут? Напиши имя сообщением.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(RegistrationStates.waiting_for_name)
