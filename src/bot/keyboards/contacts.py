"""Inline-клавиатуры для статических разделов (контакты, админ).

ТЗ §9.4: на странице «Адрес» — три кнопки (Карта, Позвонить, Админу).
Это URL-кнопки, без callback_data — Telegram сам обработает переход.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Реальные ссылки школы. URL `tel:` и `https://t.me/` Telegram умеет
# открывать без подтверждения. Для карты используем 2GIS-ссылку — она
# самая популярная в Томске для навигации.
SCHOOL_MAP_URL = "https://2gis.ru/tomsk/search/Комсомольский%2068%2F5"
SCHOOL_PHONE = "+79952928103"  # tel:-ссылка требует формат без скобок и пробелов
ADMIN_TG_URL = "https://t.me/Drum_Family_admin"


def contacts_keyboard() -> InlineKeyboardMarkup:
    """Три URL-кнопки под баннером с адресом."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗺 Открыть на карте", url=SCHOOL_MAP_URL)],
            [
                InlineKeyboardButton(text="📞 Позвонить", url=f"tel:{SCHOOL_PHONE}"),
                InlineKeyboardButton(text="💬 Админу", url=ADMIN_TG_URL),
            ],
        ]
    )


def admin_keyboard() -> InlineKeyboardMarkup:
    """Одна кнопка под текстом «Связь с админом» — прямая ссылка в чат."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Открыть чат с админом", url=ADMIN_TG_URL)],
        ]
    )
