"""Заглушка-fallback на любой текст в главном меню, не пойманный
другими роутерами.

Раньше тут жили заглушки на кнопки «🥁 Записаться», «📅 Мои занятия» и т. п.
Теперь все эти кнопки имеют реальную реализацию (booking, my_bookings,
static_info, profile). Поэтому модуль превратился в «неизвестная команда» —
ловит любые сообщения, которые не подошли ни одному предыдущему роутеру.

ВНИМАНИЕ: подключать строго ПОСЛЕДНИМ в `main.py`. Иначе он перехватит
сообщения у других handler'ов.
"""

from aiogram import Router
from aiogram.types import Message

from src.bot import texts

router = Router(name="menu_stub")

# Старое название кнопки «О школе» осталось как алиас на /contacts:
# некоторые пользователи могут помнить его. Если они напишут текст вручную —
# отвечаем тем же ABOUT_TEXT, что и раньше.
LEGACY_ABOUT = "ℹ️ О школе"


@router.message()
async def fallback(message: Message) -> None:
    # Legacy: если кто-то тапнул сохранённую где-то старую кнопку «О школе»
    if message.text == LEGACY_ABOUT:
        await message.answer(texts.ABOUT_TEXT, parse_mode="HTML")
        return
    await message.answer(texts.UNKNOWN_COMMAND)
