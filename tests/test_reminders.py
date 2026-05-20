"""Тесты RemindersScheduler (ТЗ §8.13, §8.14).

Логика проста: вокруг APScheduler.AsyncIOScheduler — но мы не хотим в
тестах поднимать реальный планировщик, поэтому мокаем `_scheduler`
после создания инстанса.

Что проверяем:
- schedule_for_booking создаёт 2 job'а на нормальной дате;
- 1 job, если занятие через 2 часа (24h offset уже в прошлом);
- 0 jobs, если занятие через 30 минут;
- 0 jobs, если datetime naive (без tzinfo);
- cancel_for_booking удаляет известные job_id, игнорирует уже сработавшие.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from apscheduler.jobstores.base import JobLookupError

from src.bot.reminders import RemindersScheduler

TOMSK = timezone(timedelta(hours=7))


@pytest.fixture
def scheduler() -> RemindersScheduler:
    """RemindersScheduler с замоканным AsyncIOScheduler внутри."""
    bot = MagicMock()
    rs = RemindersScheduler(bot)
    # Подменяем реальный AsyncIOScheduler на MagicMock — не хотим в тестах
    # реально запускать background-thread и event loop.
    rs._scheduler = MagicMock()
    return rs


def _job(job_id: str) -> MagicMock:
    j = MagicMock()
    j.id = job_id
    return j


def test_schedule_two_jobs_for_future_lesson(scheduler: RemindersScheduler) -> None:
    """Занятие через 3 дня — оба напоминания (24h и 1h) должны быть в будущем."""
    scheduler._scheduler.add_job.side_effect = [_job("j-24h"), _job("j-1h")]

    lesson = datetime.now(tz=TOMSK) + timedelta(days=3)
    scheduler.schedule_for_booking(
        record_id=42,
        telegram_id=12345,
        lesson_datetime=lesson,
        summary="🥁 X\n👤 Y\n🕒 Z",
    )

    assert scheduler._scheduler.add_job.call_count == 2
    assert scheduler.jobs_by_record == {42: ["j-24h", "j-1h"]}


def test_schedule_one_job_when_only_1h_remains(scheduler: RemindersScheduler) -> None:
    """Занятие через 2 часа — 24h-reminder уже в прошлом, остаётся только 1h."""
    scheduler._scheduler.add_job.side_effect = [_job("j-1h")]

    lesson = datetime.now(tz=TOMSK) + timedelta(hours=2)
    scheduler.schedule_for_booking(
        record_id=99, telegram_id=12345, lesson_datetime=lesson, summary="..."
    )

    assert scheduler._scheduler.add_job.call_count == 1
    assert scheduler.jobs_by_record == {99: ["j-1h"]}


def test_schedule_no_jobs_when_lesson_is_imminent(scheduler: RemindersScheduler) -> None:
    """Занятие через 30 минут — оба окна reminder'ов уже в прошлом."""
    lesson = datetime.now(tz=TOMSK) + timedelta(minutes=30)
    scheduler.schedule_for_booking(
        record_id=7, telegram_id=12345, lesson_datetime=lesson, summary="..."
    )

    scheduler._scheduler.add_job.assert_not_called()
    assert scheduler.jobs_by_record == {}


def test_schedule_rejects_naive_datetime(scheduler: RemindersScheduler) -> None:
    """datetime без tzinfo — отказ + лог, чтобы не сравнивать с aware-now."""
    naive_lesson = datetime.now() + timedelta(days=1)  # no tzinfo
    scheduler.schedule_for_booking(
        record_id=1, telegram_id=12345, lesson_datetime=naive_lesson, summary="..."
    )

    scheduler._scheduler.add_job.assert_not_called()
    assert scheduler.jobs_by_record == {}


def test_cancel_removes_known_jobs(scheduler: RemindersScheduler) -> None:
    """cancel_for_booking зовёт remove_job для всех зарегистрированных id."""
    scheduler._scheduler.add_job.side_effect = [_job("a"), _job("b")]
    lesson = datetime.now(tz=TOMSK) + timedelta(days=3)
    scheduler.schedule_for_booking(
        record_id=100, telegram_id=1, lesson_datetime=lesson, summary="."
    )

    scheduler.cancel_for_booking(100)

    assert scheduler._scheduler.remove_job.call_count == 2
    # после cancel — запись удалена из карты
    assert 100 not in scheduler.jobs_by_record


def test_cancel_ignores_already_fired_jobs(scheduler: RemindersScheduler) -> None:
    """Если job уже сработал/удалён — JobLookupError ловим, не валим."""
    # Schedule создаст 2 job'а (24h + 1h), оба «потерялись» к моменту cancel.
    scheduler._scheduler.add_job.side_effect = [_job("expired-24h"), _job("expired-1h")]
    scheduler._scheduler.remove_job.side_effect = JobLookupError("expired")

    lesson = datetime.now(tz=TOMSK) + timedelta(days=3)
    scheduler.schedule_for_booking(record_id=55, telegram_id=1, lesson_datetime=lesson, summary=".")

    # Не должно бросить
    scheduler.cancel_for_booking(55)
    assert 55 not in scheduler.jobs_by_record


def test_cancel_unknown_record_id_is_noop(scheduler: RemindersScheduler) -> None:
    """Отмена записи, которой не было в кэше — тихий ноп."""
    scheduler.cancel_for_booking(999)
    scheduler._scheduler.remove_job.assert_not_called()
