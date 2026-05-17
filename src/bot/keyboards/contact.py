"""Reply-клавиатура с кнопкой «Поделиться номером».

Используется в шаге ask_phone регистрации. `request_contact=True` — Telegram
сам отдаст контакт пользователя, не нужно парсить произвольный текст.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

SHARE_PHONE_BTN = "📱 Поделиться номером"


def share_phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=SHARE_PHONE_BTN, request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Нажми кнопку или впиши номер вручную",
    )
