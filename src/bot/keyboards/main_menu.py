"""Reply-клавиатура главного меню.

6 кнопок согласно ТЗ §9.1 (drum-family-bot-tz.md):
- 🥁 Пробный урок         📅 Моё расписание
- 💳 Стоимость            📍 Адрес
- ❓ Частые вопросы (один)
- 💬 Написать админу (один)

Кнопки «Профиль» и «Отменить запись» из меню убраны — доступны через
команды /profile и через карточки в «📅 Моё расписание» соответственно.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

# Тексты кнопок — константы, чтобы handlers могли матчить по точному тексту.
# Имена констант сохранены MENU_BOOK / MENU_MY_BOOKINGS, чтобы существующие
# handler'ы продолжали работать без переименования (важно: callback_data
# и payload не меняем, только подписи).
MENU_BOOK = "🥁 Пробный урок"
MENU_MY_BOOKINGS = "📅 Моё расписание"
MENU_PRICES = "💳 Стоимость"
MENU_CONTACTS = "📍 Адрес"
MENU_FAQ = "❓ Частые вопросы"
MENU_ADMIN = "💬 Написать админу"


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_BOOK), KeyboardButton(text=MENU_MY_BOOKINGS)],
            [KeyboardButton(text=MENU_PRICES), KeyboardButton(text=MENU_CONTACTS)],
            [KeyboardButton(text=MENU_FAQ)],
            [KeyboardButton(text=MENU_ADMIN)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери пункт меню",
    )
