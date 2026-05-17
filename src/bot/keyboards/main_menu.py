"""Reply-клавиатура главного меню.

5 пунктов из ТЗ. На этом этапе обработчики стоят заглушками
(см. `src/bot/handlers/menu_stub.py`), реальная логика появится в фичах
booking-individual-003, my-bookings-004, profile-005, booking-group-006.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

# Список кнопок вынесли в константу, чтобы handlers могли матчить по тексту.
MENU_BOOK = "🥁 Записаться"
MENU_MY_BOOKINGS = "📅 Мои занятия"
MENU_CANCEL = "❌ Отменить запись"
MENU_PROFILE = "👤 Мой профиль"
MENU_ABOUT = "ℹ️ О школе"

MENU_ITEMS = {MENU_BOOK, MENU_MY_BOOKINGS, MENU_CANCEL, MENU_PROFILE, MENU_ABOUT}


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_BOOK)],
            [KeyboardButton(text=MENU_MY_BOOKINGS), KeyboardButton(text=MENU_CANCEL)],
            [KeyboardButton(text=MENU_PROFILE), KeyboardButton(text=MENU_ABOUT)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери пункт меню",
    )
