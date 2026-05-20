"""Обработчики FAQ-карусели (ТЗ §8.10).

Поток:
1. Кнопка «❓ Частые вопросы» / `/faq` — открывается ПОДНОВЛЁННЫЙ список
   вопросов (заменяет временный placeholder из static_info.py).
2. Тап на любой вопрос — карточка edit_text с ответом + кнопка
   «← Назад к вопросам».
3. «Назад» — возвращает к списку (edit_text обратно).

Edit_text используется потому что список и карточки — это текст, не photo.
"""

import structlog
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from src.bot import texts
from src.bot.faq_data import get_faq_item
from src.bot.keyboards.faq import FAQ_BACK_DATA, FAQ_PREFIX, faq_card_keyboard, faq_list_keyboard
from src.bot.keyboards.main_menu import MENU_FAQ

log = structlog.get_logger("handlers.faq")

router = Router(name="faq")

FAQ_INTRO = (
    "❓ <b>Частые вопросы</b>\n\n"
    "Выбери вопрос — открою ответ. Если нужного нет — нажми "
    "«💬 Написать админу» в главном меню."
)


@router.message(Command("faq"))
@router.message(F.text == MENU_FAQ)
async def show_faq_list(message: Message) -> None:
    """Точка входа: показываем список вопросов."""
    await message.answer(FAQ_INTRO, parse_mode="HTML", reply_markup=faq_list_keyboard())


@router.callback_query(F.data == FAQ_BACK_DATA)
async def faq_back_to_list(callback: CallbackQuery) -> None:
    """«← Назад к вопросам» — возвращаем список."""
    if callback.message is None:
        await callback.answer()
        return
    await callback.message.edit_text(FAQ_INTRO, parse_mode="HTML", reply_markup=faq_list_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith(f"{FAQ_PREFIX}:"))
async def faq_open_item(callback: CallbackQuery) -> None:
    """Открываем карточку конкретного вопроса.

    Регистрируется ПОСЛЕ `faq_back_to_list`, потому что `_back` тоже
    начинается с `faq:`. Order-matters в роутерах: точный матч на
    `FAQ_BACK_DATA` срабатывает раньше — это важно для корректной
    маршрутизации.
    """
    if callback.data is None or callback.message is None:
        await callback.answer()
        return
    item_id = callback.data.split(":", 1)[1]
    item = get_faq_item(item_id)
    if item is None:
        # Защита от устаревшего callback_data (например, после рефакторинга FAQ).
        log.warning("faq.unknown_id", item_id=item_id)
        await callback.answer(texts.UNKNOWN_COMMAND, show_alert=True)
        return

    body = f"<b>{item.question}</b>\n\n{item.answer}"
    await callback.message.edit_text(body, parse_mode="HTML", reply_markup=faq_card_keyboard(item))
    await callback.answer()
