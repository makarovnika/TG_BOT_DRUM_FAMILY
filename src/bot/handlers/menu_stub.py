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
)

router = Router(name="menu_stub")

ABOUT_TEXT = (
    "🥁 Drum Family Томск\n\n"
    "Школа барабанов: индивидуальные и групповые занятия с тренерами.\n"
    "Скоро здесь будет вся актуальная инфа, расписание и контакты."
)

# Заглушки только для нереализованных пунктов меню. «Мой профиль» и
# «Мои занятия» реализованы — их обрабатывают profile.router и my_bookings.router.
_STUBS = {
    MENU_BOOK: (
        "🚧 Запись на занятие готовится.\n\n"
        "Здесь будет выбор: индивидуальное или групповое → услуга → "
        "преподаватель → дата → свободный слот → подтверждение записи."
    ),
    MENU_CANCEL: (
        "🚧 Отмена записи через эту кнопку готовится.\n\n"
        "А пока — открой «📅 Мои занятия» и нажми «Отменить» на нужном."
    ),
}


@router.message(F.text == MENU_ABOUT)
async def about(message: Message) -> None:
    await message.answer(ABOUT_TEXT)


@router.message(F.text.in_({MENU_BOOK, MENU_CANCEL}))
async def stub(message: Message) -> None:
    text = _STUBS.get(message.text or "", "🚧 Эта функция готовится.")
    await message.answer(text)
