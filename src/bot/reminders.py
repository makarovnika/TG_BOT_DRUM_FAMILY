"""Напоминания о занятиях (ТЗ §8.13, §8.14).

После успешной записи через `booking.confirm_booking` планируем два
сообщения для пользователя:
- за 24 часа до начала: «🥁 Напоминаю! Завтра у тебя занятие...»
- за 1 час до начала: «⏰ Через час ждём тебя на занятии...»

Реализация: in-memory APScheduler. Job-ы хранятся в памяти процесса.
При рестарте бота — теряются. Это сознательный компромисс MVP: для
персистентности нужен SQLAlchemyJobStore + миграция bot.db, и польза
сомнительна (за 100 учеников рестарты редки).

Когда понадобится персистенция — можно подменить scheduler на
AsyncIOScheduler(jobstores={'default': SQLAlchemyJobStore(url=...)}).
Никаких других правок не потребуется.

Известные ограничения:
- Если бот вырубится, а в это время должен был фаер reminder —
  он не отправится.
- Если пользователь отменит запись через админку YClients (не через
  бота) — наши job-ы про это не узнают, reminder уйдёт.
- Если у бота нет прав писать в чат (пользователь его блокировал) —
  send_message бросает TelegramForbiddenError. Ловим и логируем, чтобы
  scheduler не падал.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import structlog
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.bot import texts
from src.bot.keyboards.feedback import feedback_keyboard

log = structlog.get_logger("reminders")

REMINDER_24H_OFFSET = timedelta(hours=24)
REMINDER_1H_OFFSET = timedelta(hours=1)
# Через сколько ПОСЛЕ начала занятия слать запрос на оценку.
# 2 часа = 1 час урока + 1 час «отдыха», впечатления свежие, эмоция переварилась.
FEEDBACK_AFTER_OFFSET = timedelta(hours=2)


class RemindersScheduler:
    """Тонкая обёртка над APScheduler, заточенная под наши два кейса.

    Не наследуем AsyncIOScheduler напрямую — композиция облегчает
    мокирование в тестах.

    Состояние: `_jobs[record_id] -> list[job_id]`. По одному record_id
    может быть два job-а (24h и 1h), либо один (если 24h уже в прошлом),
    либо ноль (если занятие ближе чем через час).
    """

    def __init__(self, bot: Bot) -> None:
        self._bot = bot
        self._scheduler = AsyncIOScheduler()
        self._jobs: dict[int, list[str]] = {}

    def start(self) -> None:
        """Запускает планировщик. Вызывать один раз на старте бота."""
        self._scheduler.start()
        log.info("reminders.started")

    async def shutdown(self) -> None:
        """Останавливает планировщик. Вызывать в finally main()."""
        self._scheduler.shutdown(wait=False)
        log.info("reminders.shutdown")

    def schedule_for_booking(
        self,
        *,
        record_id: int,
        telegram_id: int,
        lesson_datetime: datetime,
        summary: str,
    ) -> None:
        """Планирует напоминания за 24ч и за 1ч до lesson_datetime.

        - `record_id` — id записи в YClients, нужен для cancel().
        - `telegram_id` — куда слать.
        - `lesson_datetime` — должен быть aware (с tzinfo).
        - `summary` — короткая HTML-строка о записи (услуга/тренер/время),
          подставляется в шаблон.

        Если время напоминания уже в прошлом — этот job не создаётся.
        Если оба в прошлом (бот тормозит / занятие через 30 минут) —
        ничего не планируется, тихо вернёт.
        """
        if lesson_datetime.tzinfo is None:
            log.warning("reminders.naive_datetime_rejected", record_id=record_id)
            return

        now = datetime.now(tz=lesson_datetime.tzinfo)
        slots = [
            ("24h", lesson_datetime - REMINDER_24H_OFFSET, texts.REMINDER_24H),
            ("1h", lesson_datetime - REMINDER_1H_OFFSET, texts.REMINDER_1H),
        ]

        scheduled: list[str] = []
        for kind, fire_at, template in slots:
            if fire_at <= now:
                continue
            job = self._scheduler.add_job(
                self._send_reminder,
                trigger="date",
                run_date=fire_at,
                kwargs={
                    "telegram_id": telegram_id,
                    "text": template.format(summary=summary),
                    "kind": kind,
                    "record_id": record_id,
                },
            )
            scheduled.append(job.id)

        if scheduled:
            self._jobs[record_id] = scheduled
            log.info(
                "reminders.scheduled",
                record_id=record_id,
                count=len(scheduled),
                lesson_datetime=lesson_datetime.isoformat(),
            )

    def schedule_feedback_for_booking(
        self,
        *,
        record_id: int,
        telegram_id: int,
        lesson_datetime: datetime,
        summary: str,
    ) -> None:
        """Через FEEDBACK_AFTER_OFFSET после начала занятия — запрос оценки 1-5.

        ID job-а добавляется в тот же `_jobs[record_id]`, что и reminder'ы.
        cancel_for_booking снимет и его.
        """
        if lesson_datetime.tzinfo is None:
            log.warning("feedback.naive_datetime_rejected", record_id=record_id)
            return

        fire_at = lesson_datetime + FEEDBACK_AFTER_OFFSET
        now = datetime.now(tz=lesson_datetime.tzinfo)
        if fire_at <= now:
            # Занятие уже прошло сильно давно — нет смысла спрашивать.
            return

        job = self._scheduler.add_job(
            self._send_feedback_request,
            trigger="date",
            run_date=fire_at,
            kwargs={
                "telegram_id": telegram_id,
                "record_id": record_id,
                "summary": summary,
            },
        )
        self._jobs.setdefault(record_id, []).append(job.id)
        log.info(
            "feedback.scheduled",
            record_id=record_id,
            fire_at=fire_at.isoformat(),
        )

    def cancel_for_booking(self, record_id: int) -> None:
        """Удаляет все запланированные напоминания для записи."""
        job_ids = self._jobs.pop(record_id, [])
        cancelled = 0
        for job_id in job_ids:
            try:
                self._scheduler.remove_job(job_id)
                cancelled += 1
            except JobLookupError:
                # Job уже сработал или удалён — это нормально, идём дальше.
                continue
        if cancelled:
            log.info("reminders.cancelled", record_id=record_id, count=cancelled)

    async def _send_reminder(
        self,
        *,
        telegram_id: int,
        text: str,
        kind: str,
        record_id: int,
    ) -> None:
        """Тело job-а: шлёт reminder. Все ошибки ловим — не валим scheduler."""
        try:
            await self._bot.send_message(telegram_id, text, parse_mode="HTML")
            log.info("reminder.sent", kind=kind, record_id=record_id, telegram_id=telegram_id)
        except TelegramAPIError as exc:
            # Например, TelegramForbiddenError если пользователь заблокировал бота.
            log.warning(
                "reminder.send_failed",
                kind=kind,
                record_id=record_id,
                telegram_id=telegram_id,
                error=str(exc),
            )

    async def _send_feedback_request(
        self,
        *,
        telegram_id: int,
        record_id: int,
        summary: str,
    ) -> None:
        """Тело job-а: шлёт запрос оценки с inline-кнопками 1-5."""
        try:
            await self._bot.send_message(
                telegram_id,
                texts.FEEDBACK_ASK.format(summary=summary),
                parse_mode="HTML",
                reply_markup=feedback_keyboard(record_id),
            )
            log.info("feedback.sent", record_id=record_id, telegram_id=telegram_id)
        except TelegramAPIError as exc:
            log.warning(
                "feedback.send_failed",
                record_id=record_id,
                telegram_id=telegram_id,
                error=str(exc),
            )

    # ---------- для тестов ----------

    @property
    def jobs_by_record(self) -> dict[int, list[str]]:
        """Текущее состояние карты record_id → job_ids. Read-only-вид для тестов."""
        return dict(self._jobs)
