"""Inline-клавиатура для оценки занятия 1-5 (ТЗ §8.15).

callback_data: `fb:{record_id}:{rating}`.
Включаем record_id чтобы:
- связать оценку с конкретной записью в feedbacks-таблице,
- ловить старые callback'и (если кэш Telegram задержался) и не путать
  с новой оценкой.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

FEEDBACK_PREFIX = "fb"

# Звёзды-числа отдельно: текст кнопки + значение, которое уйдёт в БД.
_STAR_BUTTONS = [(1, "⭐"), (2, "⭐⭐"), (3, "⭐⭐⭐"), (4, "⭐⭐⭐⭐"), (5, "⭐⭐⭐⭐⭐")]


def feedback_keyboard(record_id: int) -> InlineKeyboardMarkup:
    """5 кнопок звёзд по одной в строке (для удобства тычка на мобильном)."""
    rows = [
        [
            InlineKeyboardButton(
                text=label,
                callback_data=f"{FEEDBACK_PREFIX}:{record_id}:{rating}",
            )
        ]
        for rating, label in _STAR_BUTTONS
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
