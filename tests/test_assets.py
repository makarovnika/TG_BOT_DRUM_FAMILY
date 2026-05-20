"""Тесты на src/bot/assets.py — функция banner().

Простая, но важная — путь к файлам берётся относительно `__file__`, и
если кто-то переименует директорию assets/banners/ или перенесёт модуль
выше/ниже по иерархии — banner() сломается. Эти тесты ловят такую
регрессию на этапе CI.
"""

from pathlib import Path

from aiogram.types import FSInputFile

from src.bot.assets import banner


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
