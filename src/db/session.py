"""Фабрика async-сессий SQLAlchemy.

Дизайн:
- движок и фабрика сессий создаются функцией `create_engine()`, а не глобально,
  чтобы тесты могли поднять отдельный in-memory SQLite, не трогая прод;
- в проде `main.py` один раз вызывает `create_engine(get_settings().database_url)`
  и держит результат у себя в замыкании;
- `init_db(engine)` создаёт таблицы — нужен на первом запуске
  и в тестах (Base.metadata.create_all).
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.db.models import Base


def create_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    """Создаёт async-движок SQLAlchemy.

    `echo=True` включает вывод всех SQL-запросов — удобно для отладки,
    но шумно в обычной работе.
    """
    return create_async_engine(database_url, echo=echo)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Создаёт фабрику сессий, привязанную к движку.

    `expire_on_commit=False` — стандартная практика для async: иначе после
    commit() обращение к атрибутам объекта триггерит implicit refresh,
    что в async-коде ломает поток (нужен await).
    """
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    """Создаёт все таблицы в БД, если их ещё нет.

    Для MVP этого достаточно — миграции через Alembic не нужны,
    схема стабильная. Когда схема начнёт меняться в проде — переедем на Alembic.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
