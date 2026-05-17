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

from src.bot.keyboards.main_menu import MENU_ABOUT, MENU_CANCEL

router = Router(name="menu_stub")

ABOUT_TEXT = (
    "🥁 Drum Family Томск\n\n"
    "Школа барабанов: индивидуальные и групповые занятия с тренерами.\n"
    "Скоро здесь будет вся актуальная инфа, расписание и контакты."
)

CANCEL_STUB = (
    "🚧 Отмена через эту кнопку готовится.\n\n"
    "А пока — открой «📅 Мои занятия» и нажми «Отменить» под нужной записью."
)


@router.message(F.text == MENU_ABOUT)
async def about(message: Message) -> None:
    await message.answer(ABOUT_TEXT)


@router.message(F.text == MENU_CANCEL)
async def cancel_stub(message: Message) -> None:
    await message.answer(CANCEL_STUB)
