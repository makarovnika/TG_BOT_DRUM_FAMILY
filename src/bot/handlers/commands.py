"""Сервисные команды: /cancel, /help.

/start живёт отдельно (src/bot/handlers/start.py) — у него своя логика
ветвления «зарегистрирован/новый».
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from src.bot.keyboards.main_menu import main_menu_kb
from src.services.user_service import UserService

router = Router(name="commands")


@router.message(Command("cancel"))
async def cmd_cancel(
    message: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    """Отмена любого текущего диалога (FSM).

    Если пользователь зарегистрирован — возвращаем в главное меню.
    Если нет — просто чистим состояние, на следующий /start пройдёт регистрацию.
    """
    current = await state.get_state()
    await state.clear()

    if current is None:
        await message.answer("Нечего отменять — ты не в середине диалога.")
        return

    if message.from_user is None:
        await message.answer("Окей, диалог сброшен.", reply_markup=ReplyKeyboardRemove())
        return

    existing = await user_service.find_by_telegram_id(message.from_user.id)
    if existing is not None:
        await message.answer("Окей, отменил. Возвращаю в меню.", reply_markup=main_menu_kb())
    else:
        await message.answer(
            "Окей, диалог сброшен. Чтобы начать заново — отправь /start.",
            reply_markup=ReplyKeyboardRemove(),
        )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Подсказка по доступным командам."""
    await message.answer(
        "Команды бота:\n\n"
        "/start — главное меню (или регистрация, если ты тут впервые)\n"
        "/cancel — отменить текущий диалог (например, если застрял в регистрации)\n"
        "/help — эта подсказка\n\n"
        "Кнопки главного меню:\n"
        "🥁 Записаться — записаться на занятие (скоро будет)\n"
        "📅 Мои занятия — список твоих будущих занятий (скоро)\n"
        "❌ Отменить запись — отмена записи на занятие (скоро)\n"
        "👤 Мой профиль — твои данные и абонемент (скоро)\n"
        "ℹ️ О школе — контакты и информация"
    )
