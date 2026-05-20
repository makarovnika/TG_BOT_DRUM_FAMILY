"""Inline-клавиатуры для FSM записи на занятие.

Все callback_data используют префиксы — чтобы handler знал, какому шагу
принадлежит callback (на случай, если пользователь жмёт устаревшую кнопку).

Размер callback_data: лимит Telegram = 64 байта. Самый длинный кейс —
slot ISO (`slot:2026-05-18T13:30:00+07:00` ≈ 30 байт) — укладывается.
"""

from datetime import date as date_cls

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Префиксы callback_data
AGE_PREFIX = "bk_age"
SERVICE_PREFIX = "bk_svc"
STAFF_PREFIX = "bk_stf"
DATE_PREFIX = "bk_dt"
SLOT_PREFIX = "bk_sl"
CONFIRM_PREFIX = "bk_cnf"
CANCEL_DATA = "bk_cancel"

# Возрастные группы (ТЗ §9.2). id используется в callback_data, label —
# на кнопке. Порядок здесь = порядок отображения.
AGE_GROUPS: tuple[tuple[str, str], ...] = (
    ("kid", "🧒 Ребёнку 7–12"),
    ("teen", "🎸 Подростку 13–17"),
    ("student", "🎓 Студенту 18–25"),
    ("adult", "🙋 Взрослому 25+"),
)
AGE_GROUP_LABELS: dict[str, str] = dict(AGE_GROUPS)

_MONTHS_RU = (
    "янв",
    "фев",
    "мар",
    "апр",
    "май",
    "июн",
    "июл",
    "авг",
    "сен",
    "окт",
    "ноя",
    "дек",
)


def _row_cancel() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text="↩️ Отмена", callback_data=CANCEL_DATA)]


def age_keyboard() -> InlineKeyboardMarkup:
    """4 возрастные группы по 2 в ряд (ТЗ §9.2)."""
    rows: list[list[InlineKeyboardButton]] = []
    cur: list[InlineKeyboardButton] = []
    for age_id, label in AGE_GROUPS:
        cur.append(InlineKeyboardButton(text=label, callback_data=f"{AGE_PREFIX}:{age_id}"))
        if len(cur) == 2:
            rows.append(cur)
            cur = []
    if cur:
        rows.append(cur)
    rows.append(_row_cancel())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def services_keyboard(services: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """services: [(id, title), ...]."""
    rows = [
        [InlineKeyboardButton(text=title, callback_data=f"{SERVICE_PREFIX}:{sid}")]
        for sid, title in services
    ]
    rows.append(_row_cancel())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def staff_keyboard(staff: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """staff: [(id, name), ...]."""
    rows = [
        [InlineKeyboardButton(text=name, callback_data=f"{STAFF_PREFIX}:{sid}")]
        for sid, name in staff
    ]
    rows.append(_row_cancel())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def dates_keyboard(dates: list[str]) -> InlineKeyboardMarkup:
    """dates: список ISO 'YYYY-MM-DD'. Сортируем по возрастанию, рисуем
    кнопками `18 май`, `19 май`, ... по 3 в ряд для компактности."""
    sorted_dates = sorted(dates)
    rows: list[list[InlineKeyboardButton]] = []
    cur: list[InlineKeyboardButton] = []
    for iso in sorted_dates:
        try:
            d = date_cls.fromisoformat(iso)
            label = f"{d.day} {_MONTHS_RU[d.month - 1]}"
        except ValueError:
            label = iso
        cur.append(InlineKeyboardButton(text=label, callback_data=f"{DATE_PREFIX}:{iso}"))
        if len(cur) == 3:
            rows.append(cur)
            cur = []
    if cur:
        rows.append(cur)
    rows.append(_row_cancel())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def slots_keyboard(slots: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """slots: [(time_label, datetime_iso), ...]. По 3 в ряд."""
    rows: list[list[InlineKeyboardButton]] = []
    cur: list[InlineKeyboardButton] = []
    for label, dt_iso in slots:
        cur.append(InlineKeyboardButton(text=label, callback_data=f"{SLOT_PREFIX}:{dt_iso}"))
        if len(cur) == 3:
            rows.append(cur)
            cur = []
    if cur:
        rows.append(cur)
    rows.append(_row_cancel())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Записаться", callback_data=f"{CONFIRM_PREFIX}:yes"),
                InlineKeyboardButton(text="↩️ Отмена", callback_data=CANCEL_DATA),
            ]
        ]
    )


def post_booking_keyboard(record_id: int) -> InlineKeyboardMarkup:
    """Кнопки под сообщением «✅ Записал!» по ТЗ §9.5.

    «Перенести» через бота сейчас не реализовано (отдельная фича), поэтому
    кнопку не показываем — чтобы не вводить в заблуждение. Оставляем
    «Отменить» (используется тот же callback_data, что в «📅 Моё расписание»)
    и «Маршрут на карте» как URL-кнопку.
    """
    # Импорт здесь, чтобы избежать циклической зависимости с bookings.py
    # (там Cancel-кнопка для уже созданных записей).
    from src.bot.keyboards.bookings import CANCEL_PREFIX
    from src.bot.keyboards.contacts import SCHOOL_MAP_URL

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✕ Отменить", callback_data=f"{CANCEL_PREFIX}:{record_id}"
                ),
            ],
            [
                InlineKeyboardButton(text="🗺 Маршрут на карте", url=SCHOOL_MAP_URL),
            ],
        ]
    )
