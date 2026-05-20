"""Inline-клавиатуры для FAQ-карусели (ТЗ §8.10, §9.5).

Структура:
- список вопросов как inline-кнопки (по одной на строку для читаемости);
- внутри карточки вопроса — кнопки «← Назад к вопросам» и «🥁 Записаться».

callback_data:
- `faq:{item_id}` — открыть карточку конкретного вопроса;
- `faq:_back` — вернуться к списку (underscore-prefix защищает от
  совпадения с реальным item_id, если в будущем кто-то добавит id="back").
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.faq_data import FAQ_ITEMS, FaqItem
from src.bot.keyboards.main_menu import MENU_BOOK

FAQ_PREFIX = "faq"
FAQ_BACK_DATA = f"{FAQ_PREFIX}:_back"


def faq_list_keyboard() -> InlineKeyboardMarkup:
    """Список всех вопросов — по одному в строке."""
    rows = [
        [InlineKeyboardButton(text=item.question, callback_data=f"{FAQ_PREFIX}:{item.id}")]
        for item in FAQ_ITEMS
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def faq_card_keyboard(item: FaqItem) -> InlineKeyboardMarkup:
    """Под открытой карточкой — назад к списку + «к записи».

    Кнопка «🥁 Записаться» работает как ссылка-намёк: она имеет
    callback_data c префиксом FAQ_PREFIX, но ловится в booking-handler'е
    как переход в booking-FSM. Для простоты — пока reply-кнопкой через
    callback не сделать, оставляем явное «← Назад к вопросам».
    """
    del item  # сейчас id не нужен на кнопках — оставлено в сигнатуре для будущего
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="← Назад к вопросам", callback_data=FAQ_BACK_DATA)],
            # Подсказка: чтобы записаться, можно ткнуть кнопку главного меню.
            # Здесь без callback — пользователь сам нажмёт нужную reply-кнопку.
            # (Через inline нельзя «отправить» текст MENU_BOOK от имени юзера.)
        ]
    )


__all__ = [
    "FAQ_BACK_DATA",
    "FAQ_PREFIX",
    "MENU_BOOK",  # реэкспорт для возможной интеграции в будущем
    "faq_card_keyboard",
    "faq_list_keyboard",
]
