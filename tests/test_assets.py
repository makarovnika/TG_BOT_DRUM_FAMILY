"""Тесты на src/bot/assets.py — функция banner() + file_id-кэш.

Простая, но важная — путь к файлам берётся относительно `__file__`, и
если кто-то переименует директорию assets/banners/ или перенесёт модуль
выше/ниже по иерархии — banner() сломается. Эти тесты ловят такую
регрессию на этапе CI.

Также тесты на кэш: после remember_banner следующий banner() должен
вернуть строку file_id, а не FSInputFile.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from aiogram.types import FSInputFile

from src.bot.assets import banner, clear_banner_cache, remember_banner


@pytest.fixture(autouse=True)
def _isolate_cache():
    """Каждый тест начинается с пустого кэша — иначе порядок тестов
    влияет на результат."""
    clear_banner_cache()
    yield
    clear_banner_cache()


def test_banner_returns_fs_input_file() -> None:
    """Функция возвращает FSInputFile, не строку и не Path."""
    result = banner("welcome")
    assert isinstance(result, FSInputFile)


def test_banner_path_resolves_inside_project() -> None:
    """Путь указывает на реально существующий файл в проекте.

    Тест валит регрессию, если случайно поломают вычисление _PROJECT_ROOT
    в src/bot/assets.py (например, поменяют parents[2] на parents[1]).
    """
    result = banner("welcome")
    # FSInputFile.path — это абсолютный pathlib.Path или строка
    path = Path(result.path)
    assert path.exists(), f"Баннер по пути {path} не существует"
    assert path.suffix == ".png"


def test_banner_naming_convention() -> None:
    """Файлы лежат строго как `{name}-1280x640.png`."""
    for name in ("welcome", "trial", "contacts", "schedule"):
        result = banner(name)
        assert Path(result.path).name == f"{name}-1280x640.png"
        assert Path(result.path).exists(), f"{name}: файл не найден"


def test_banner_unknown_name_does_not_crash() -> None:
    """Несуществующий баннер не падает в banner() — упадёт позже на send_photo
    с понятной ошибкой Telegram. Это сознательный дизайн (см. docstring)."""
    # FSInputFile создаётся ленивым — на этапе создания файл не открывается.
    result = banner("nonexistent")
    assert isinstance(result, FSInputFile)
    # Файла нет — но это поймёт только Telegram при попытке отправить.
    assert not Path(result.path).exists()


# ---------- file_id кэш ----------


def _make_message_with_photo(file_id: str) -> MagicMock:
    """Mock Message с .photo[].file_id, как возвращает Telegram после send_photo."""
    msg = MagicMock()
    photo_size = MagicMock()
    photo_size.file_id = file_id
    msg.photo = [photo_size]
    return msg


def test_remember_banner_caches_file_id() -> None:
    """После remember_banner следующий banner() возвращает строку file_id."""
    msg = _make_message_with_photo("AgACAg-CACHED-ID")
    remember_banner("welcome", msg)

    result = banner("welcome")
    assert isinstance(result, str)
    assert result == "AgACAg-CACHED-ID"


def test_banner_cache_is_per_name() -> None:
    """Кэшированный welcome не путает trial."""
    msg = _make_message_with_photo("welcome-fid")
    remember_banner("welcome", msg)

    # welcome закэширован, trial — нет
    assert banner("welcome") == "welcome-fid"
    assert isinstance(banner("trial"), FSInputFile)


def test_remember_banner_overwrites() -> None:
    """Повторный remember с тем же name перезаписывает file_id."""
    msg1 = _make_message_with_photo("first-fid")
    msg2 = _make_message_with_photo("second-fid")

    remember_banner("trial", msg1)
    remember_banner("trial", msg2)

    assert banner("trial") == "second-fid"


def test_remember_banner_no_photo_silently_skips() -> None:
    """Если у message нет .photo (странный кейс) — кэш не пополняется,
    но и не падает."""
    msg = MagicMock()
    msg.photo = None

    # Не должно бросить
    remember_banner("contacts", msg)

    # Кэш пустой — banner вернёт FSInputFile
    assert isinstance(banner("contacts"), FSInputFile)


def test_clear_banner_cache_empties_all() -> None:
    """clear() сбрасывает все имена сразу."""
    for name in ("welcome", "trial", "contacts", "schedule"):
        remember_banner(name, _make_message_with_photo(f"{name}-fid"))

    # все закэшированы
    for name in ("welcome", "trial", "contacts", "schedule"):
        assert isinstance(banner(name), str)

    clear_banner_cache()

    # все снова FSInputFile
    for name in ("welcome", "trial", "contacts", "schedule"):
        assert isinstance(banner(name), FSInputFile)
