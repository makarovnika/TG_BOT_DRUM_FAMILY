"""Inline-клавиатуры для работы с записями (мои занятия + отмена).

Кнопка «Отменить» — inline (под карточкой записи), а не reply, потому
что reply-клавиатура заменяет главное меню, что плохо для UX. Inline
button прикрепляется к конкретному сообщению-карточке.

callback_data: `cancel:<record_id>` → handler парсит и зовёт API.
Префикс нужен, чтобы можно было добавить другие inline-действия в
будущем (типа `reschedule:<id>`).
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CANCEL_PREFIX = "cancel"
CANCEL_CONFIRM_PREFIX = "cancel_confirm"
CANCEL_DECLINE = "cancel_decline"


def cancel_button(record_id: int) -> InlineKeyboardMarkup:
    """Клавиатура «Отменить» под карточкой одной записи."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"{CANCEL_PREFIX}:{record_id}",
                )
            ]
        ]
    )


def cancel_confirm_keyboard(record_id: int) -> InlineKeyboardMarkup:
    """Подтверждение отмены — две кнопки «Да, отменить» / «Нет, оставить»."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, отменить",
                    callback_data=f"{CANCEL_CONFIRM_PREFIX}:{record_id}",
                ),
                InlineKeyboardButton(
                    text="↩️ Нет, оставить",
                    callback_data=CANCEL_DECLINE,
                ),
            ]
        ]
    )
