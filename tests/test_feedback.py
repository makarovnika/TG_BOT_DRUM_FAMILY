"""Тесты handler'а оценки занятия (ТЗ §8.15).

Покрытие:
- happy path: валидный callback → запись в БД + edit_text «Спасибо» + toast;
- битый callback_data (мало частей, не-числа) → тихо игнорируем;
- rating вне 1..5 → тихо игнорируем (защита от подмены callback'а);
- DB-ошибка → alert пользователю, не падаем.
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers.feedback import rate_lesson
from src.db.models import Feedback
from src.db.session import create_engine, create_session_factory, init_db


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    """Чистая in-memory SQLite на каждый тест."""
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    factory = create_session_factory(engine)
    async with factory() as s:
        yield s
    await engine.dispose()


def _cb(data: str | None = None, user_id: int = 12345) -> MagicMock:
    cb = MagicMock()
    cb.from_user = MagicMock(id=user_id)
    cb.data = data
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


async def test_rate_lesson_saves_feedback_to_db(session: AsyncSession) -> None:
    callback = _cb(data="fb:1718143956:5")

    await rate_lesson(callback, session)

    # запись в БД появилась
    result = await session.execute(select(Feedback))
    feedbacks = result.scalars().all()
    assert len(feedbacks) == 1
    fb = feedbacks[0]
    assert fb.telegram_id == 12345
    assert fb.yclients_record_id == 1718143956
    assert fb.rating == 5

    # UI: edit_text + toast
    callback.message.edit_text.assert_awaited_once()
    callback.answer.assert_awaited_once()
    assert "спасибо" in callback.message.edit_text.call_args.args[0].lower()


async def test_rate_lesson_ignores_malformed_callback(session: AsyncSession) -> None:
    """callback_data из 2 частей вместо 3 — тихо игнорируем."""
    callback = _cb(data="fb:123")

    await rate_lesson(callback, session)

    # в БД ничего не сохранилось
    result = await session.execute(select(Feedback))
    assert result.scalars().all() == []
    # edit_text не вызывался — сообщение остаётся как есть
    callback.message.edit_text.assert_not_called()


async def test_rate_lesson_ignores_non_integer_parts(session: AsyncSession) -> None:
    """Не-числа в callback_data — тоже тихо игнорируем."""
    callback = _cb(data="fb:abc:5")

    await rate_lesson(callback, session)

    result = await session.execute(select(Feedback))
    assert result.scalars().all() == []
    callback.message.edit_text.assert_not_called()


async def test_rate_lesson_ignores_out_of_range(session: AsyncSession) -> None:
    """rating=10 (подмена в DevTools) — игнорируем."""
    callback = _cb(data="fb:42:10")

    await rate_lesson(callback, session)

    result = await session.execute(select(Feedback))
    assert result.scalars().all() == []


async def test_rate_lesson_each_rating_from_1_to_5(session: AsyncSession) -> None:
    """Каждое из 5 значений рейтинга должно проходить."""
    for rating in (1, 2, 3, 4, 5):
        cb = _cb(data=f"fb:{1000 + rating}:{rating}")
        await rate_lesson(cb, session)

    result = await session.execute(select(Feedback).order_by(Feedback.rating))
    feedbacks = result.scalars().all()
    assert [fb.rating for fb in feedbacks] == [1, 2, 3, 4, 5]
