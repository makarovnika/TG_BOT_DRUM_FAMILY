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

# Конкретные сообщения вместо общего «функция в разработке» — пользователю
# понятно, что именно и когда появится. Сейчас все четыре пункта помечены
# «🚧 готовится» с человеческим описанием того, что внутри будет.
_STUBS = {
    MENU_BOOK: (
        "🚧 Запись на занятие готовится.\n\n"
        "Здесь будет выбор: индивидуальное или групповое → услуга → "
        "преподаватель → дата → свободный слот → подтверждение записи."
    ),
    MENU_MY_BOOKINGS: (
        "🚧 Список твоих будущих занятий готовится.\n\n"
        "Тут появятся карточки с датой, временем, преподавателем и залом, "
        "по каждой — кнопка «Отменить» (если до начала больше 24 часов)."
    ),
    MENU_CANCEL: (
        "🚧 Отмена записи готовится.\n\n"
        "Сейчас отмену можно сделать только через админку YClients или "
        "позвонив в школу."
    ),
    MENU_PROFILE: (
        "🚧 Профиль готовится.\n\n"
        "Тут будет твоё имя, телефон и количество оставшихся занятий по "
        "абонементу."
    ),
}


@router.message(F.text == MENU_ABOUT)
async def about(message: Message) -> None:
    await message.answer(ABOUT_TEXT)


@router.message(F.text.in_({MENU_BOOK, MENU_MY_BOOKINGS, MENU_CANCEL, MENU_PROFILE}))
async def stub(message: Message) -> None:
    text = _STUBS.get(message.text or "", "🚧 Эта функция готовится.")
    await message.answer(text)
