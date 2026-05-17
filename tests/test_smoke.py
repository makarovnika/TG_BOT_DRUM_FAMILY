"""Базовые smoke-тесты: проверяют, что харнесс вообще работает.

Эти тесты намеренно не зависят от .env и от BOT_TOKEN — они должны проходить
сразу после `uv sync`, ещё до того, как пользователь заполнит токены.
"""

import sys


def test_python_version() -> None:
    """Pytest, ruff и сам проект работают на Python 3.11+."""
    assert sys.version_info >= (3, 11), f"Нужен Python 3.11+, найден {sys.version}"


def test_can_import_src() -> None:
    """Пакет `src` импортируется (нет синтаксических ошибок в каркасе)."""
    import src  # noqa: F401
