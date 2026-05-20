"""Подгрузка визуальных ассетов из assets/banners/ + file_id-кэш.

Зачем кэш:
- При первой отправке Telegram возвращает file_id для загруженного фото.
- Запоминаем file_id в памяти процесса по имени баннера.
- Следующие send_photo шлют не PNG-файл, а строку file_id — это в разы
  быстрее (нет HTTP-загрузки) и не грузит сеть.

Жизненный цикл:
- Кэш живёт ровно один процесс бота. После рестарта пуст — первая
  отправка снова загрузит PNG (Telegram примет либо file_id, либо файл).
- Это намеренно: file_id живут долго, но мы не хотим SQLite-таблицу
  ради такой оптимизации.

Использование в handler'е:

    msg = await message.answer_photo(banner("welcome"), caption=...)
    remember_banner("welcome", msg)

Тесты используют `clear_banner_cache()` в фикстуре, чтобы каждый тест
видел свежее состояние.
"""

from pathlib import Path

from aiogram.types import FSInputFile, Message

# Корень проекта — три уровня вверх от src/bot/assets.py
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_BANNERS_DIR = _PROJECT_ROOT / "assets" / "banners"

# Модульный синглтон: {name: file_id}. Process-scoped.
# Защищать lock'ом не нужно — Python single-threaded на уровне dict-ops,
# а GIL гарантирует атомарность `get`/`__setitem__` для CPython.
_banner_cache: dict[str, str] = {}


def banner(name: str) -> str | FSInputFile:
    """Возвращает file_id из кэша (строка) или FSInputFile.

    - `name` без суффикса `-1280x640.png`: welcome, trial, contacts, schedule.
    - Если file_id уже в кэше — возвращаем строку (Telegram принимает её
      в `photo=...` напрямую).
    - Иначе возвращаем FSInputFile, чтобы реально загрузить PNG.

    После успешного send_photo не забудь вызвать `remember_banner(name, msg)`,
    чтобы запомнить file_id для следующих отправок.
    """
    cached = _banner_cache.get(name)
    if cached is not None:
        return cached
    return FSInputFile(_BANNERS_DIR / f"{name}-1280x640.png")


def remember_banner(name: str, message: Message) -> None:
    """Сохраняет file_id из ответа Telegram в кэш.

    `message` — возврат `answer_photo` / `send_photo`. Telegram-объект
    Message содержит список `photo` с разными размерами; берём ПОСЛЕДНИЙ
    (это файл максимального размера, его-то и стоит кэшировать).

    Если у message нет .photo (странный кейс) — молча ничего не делаем,
    в следующий раз снова загрузим из файла.
    """
    if not message.photo:
        return
    file_id = message.photo[-1].file_id
    _banner_cache[name] = file_id


def clear_banner_cache() -> None:
    """Сбрасывает кэш. Нужно в тестах между прогонами, чтобы один тест
    не подмешивал состояние другому."""
    _banner_cache.clear()
