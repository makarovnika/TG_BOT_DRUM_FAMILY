"""Статические разделы: Адрес, Стоимость, FAQ, Админ.

Каждый — это нажатие кнопки из главного меню ИЛИ слэш-команда
(`/contacts`, `/prices`, `/faq`, `/admin`). Текст один для обоих способов
вызова — берётся из `src.bot.texts`.

В будущем сюда можно вкрутить inline-кнопки (карта, позвонить и т. п.),
сейчас всё текстовое.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from src.bot import texts
from src.bot.assets import banner
from src.bot.keyboards.main_menu import (
    MENU_ADMIN,
    MENU_CONTACTS,
    MENU_FAQ,
    MENU_PRICES,
)

router = Router(name="static_info")


# ---------- Адрес / контакты ----------


@router.message(Command("contacts"))
@router.message(F.text == MENU_CONTACTS)
async def show_contacts(message: Message) -> None:
    # Баннер «200 м² драйва» + адрес/телефон/часы работы в caption.
    await message.answer_photo(
        photo=banner("contacts"),
        caption=texts.CONTACTS_TEXT,
        parse_mode="HTML",
    )


# ---------- Стоимость ----------


@router.message(Command("prices"))
@router.message(F.text == MENU_PRICES)
async def show_prices(message: Message) -> None:
    await message.answer(texts.PRICES_TEXT_PLACEHOLDER, parse_mode="HTML")


# ---------- FAQ ----------


@router.message(Command("faq"))
@router.message(F.text == MENU_FAQ)
async def show_faq(message: Message) -> None:
    await message.answer(texts.FAQ_TEXT_PLACEHOLDER, parse_mode="HTML")


# ---------- Админ ----------


@router.message(Command("admin"))
@router.message(F.text == MENU_ADMIN)
async def show_admin(message: Message) -> None:
    await message.answer(texts.ADMIN_TEXT, parse_mode="HTML")
