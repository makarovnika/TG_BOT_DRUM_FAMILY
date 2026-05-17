"""Заглушки на пункты главного меню.

Чтобы зарегистрированный пользователь, нажав на кнопку, не упирался в
молчание бота. Реальная логика будет в:
- booking-individual-003 (Записаться);
- my-bookings-004 (Мои занятия + Отменить);
- profile-005 (Мой профиль);
- booking-group-006 (групповая ветка).

«О школе» — статический текст, можно сделать сразу.
"""

from aiogram import F, Router
from aiogram.types import Message

from src.bot.keyboards.main_menu import (
    MENU_ABOUT,
    MENU_BOOK,
    MENU_CANCEL,
    MENU_MY_BOOKINGS,
    MENU_PROFILE,
)

router = Router(name="menu_stub")

ABOUT_TEXT = (
    "🥁 Drum Family Томск\n\n"
    "Школа барабанов: индивидуальные и групповые занятия с тренерами.\n"
    "Скоро здесь будет вся актуальная инфа, расписание и контакты."
)

NOT_READY_TEXT = "Эта функция пока в разработке. Скоро добавлю!"


@router.message(F.text == MENU_ABOUT)
async def about(message: Message) -> None:
    await message.answer(ABOUT_TEXT)


@router.message(F.text.in_({MENU_BOOK, MENU_MY_BOOKINGS, MENU_CANCEL, MENU_PROFILE}))
async def stub(message: Message) -> None:
    await message.answer(NOT_READY_TEXT)
