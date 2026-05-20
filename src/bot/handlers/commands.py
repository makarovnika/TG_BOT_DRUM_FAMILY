"""Сервисные команды: /cancel, /help, /trial, /schedule, /profile.

/start живёт отдельно (src/bot/handlers/start.py) — у него своя логика
ветвления «зарегистрирован/новый».

/contacts, /prices, /faq, /admin — в src/bot/handlers/static_info.py.

Команды-алиасы (/trial, /schedule, /profile) ведут в те же handler'ы,
что и кнопки главного меню — это удобно для пользователя, который
привык вводить команды.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from src.bot import texts
from src.bot.handlers.booking import start_booking
from src.bot.handlers.my_bookings import show_my_bookings
from src.bot.handlers.profile import show_profile
from src.bot.keyboards.main_menu import main_menu_kb
from src.services.user_service import UserService
from src.yclients.client import YClientsClient

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
        await message.answer(texts.CANCEL_NOTHING_TO_CANCEL)
        return

    if message.from_user is None:
        await message.answer(texts.CANCEL_DIALOG_RESET_NEW, reply_markup=ReplyKeyboardRemove())
        return

    existing = await user_service.find_by_telegram_id(message.from_user.id)
    if existing is not None:
        await message.answer(texts.CANCEL_DIALOG_RESET_REGISTERED, reply_markup=main_menu_kb())
    else:
        await message.answer(texts.CANCEL_DIALOG_RESET_NEW, reply_markup=ReplyKeyboardRemove())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Подсказка по доступным командам."""
    await message.answer(texts.HELP_TEXT)


# ---------- алиасы на пункты меню ----------


@router.message(Command("trial"))
async def cmd_trial(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    yclients: YClientsClient,
) -> None:
    """`/trial` — алиас на кнопку «🥁 Пробный урок»."""
    await start_booking(message, state, user_service, yclients)


@router.message(Command("schedule"))
async def cmd_schedule(
    message: Message,
    user_service: UserService,
    yclients: YClientsClient,
) -> None:
    """`/schedule` — алиас на кнопку «📅 Моё расписание»."""
    await show_my_bookings(message, user_service, yclients)


@router.message(Command("profile"))
async def cmd_profile(
    message: Message,
    user_service: UserService,
    yclients: YClientsClient,
) -> None:
    """`/profile` — профиль доступен только через команду (в меню убран)."""
    await show_profile(message, user_service, yclients)
