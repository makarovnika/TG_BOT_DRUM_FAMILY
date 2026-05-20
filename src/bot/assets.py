"""Подгрузка визуальных ассетов из assets/banners/.

Используется в handler'ах вместо `message.answer(...)`, когда нужно
отправить картинку + caption.

Простой путь — каждый раз отправлять файл (FSInputFile). Telegram кэширует
file_id на своей стороне, но переиспользовать его между запусками бота
нельзя без сохранения в БД. Для нашего объёма (100 учеников) ок.

Если в продакшене захочется быстрее — сохранить file_id после первой
отправки в SQLite и переиспользовать.
"""

from pathlib import Path

from aiogram.types import FSInputFile

# Корень проекта — три уровня вверх от src/bot/assets.py
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_BANNERS_DIR = _PROJECT_ROOT / "assets" / "banners"


def banner(name: str) -> FSInputFile:
    """Имя без `-1280x640.png` суффикса: welcome, trial, contacts, schedule.

    Если файла нет — Telegram упадёт с понятной ошибкой на send_photo.
    Намеренно не делаем мягкий fallback: лучше явная ошибка, чем сообщение
    без баннера незаметно.
    """
    return FSInputFile(_BANNERS_DIR / f"{name}-1280x640.png")
