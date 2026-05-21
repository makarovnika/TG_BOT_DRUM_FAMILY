"""Обработчик нажатия на звезду в feedback-сообщении.

Поток:
1. Через 2 часа после lesson_datetime scheduler шлёт сообщение с 5
   кнопками-звёздами (см. RemindersScheduler.schedule_feedback_for_booking).
2. Пользователь жмёт звезду — этот handler:
   - валидирует rating (1-5);
   - сохраняет Feedback в SQLite (telegram_id + record_id + rating);
   - edit_text на «Спасибо за оценку!»;
   - убирает inline-клавиатуру, чтобы повторное нажатие не плодило записи.
"""

import structlog
from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot import texts
from src.bot.keyboards.feedback import FEEDBACK_PREFIX
from src.db.models import Feedback

log = structlog.get_logger("handlers.feedback")

router = Router(name="feedback")


@router.callback_query(F.data.startswith(f"{FEEDBACK_PREFIX}:"))
async def rate_lesson(callback: CallbackQuery, session: AsyncSession) -> None:
    """Принимает оценку от пользователя и сохраняет в БД."""
    if callback.data is None or callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    # callback_data формат: fb:{record_id}:{rating}
    parts = callback.data.split(":")
    if len(parts) != 3:
        log.warning("feedback.bad_callback_data", data=callback.data)
        await callback.answer()
        return

    try:
        record_id = int(parts[1])
        rating = int(parts[2])
    except ValueError:
        log.warning("feedback.parse_failed", data=callback.data)
        await callback.answer()
        return

    if not 1 <= rating <= 5:
        log.warning("feedback.out_of_range", rating=rating)
        await callback.answer()
        return

    feedback = Feedback(
        telegram_id=callback.from_user.id,
        yclients_record_id=record_id,
        rating=rating,
    )
    session.add(feedback)
    try:
        await session.commit()
    except SQLAlchemyError as exc:
        # Идёт через middleware, session закроется. Просто логируем.
        log.exception("feedback.db_error", error=str(exc))
        await callback.answer("Не получилось сохранить. Попробуй позже.", show_alert=True)
        return

    log.info(
        "feedback.received",
        telegram_id=callback.from_user.id,
        record_id=record_id,
        rating=rating,
    )

    # edit_text + reply_markup=None: убираем кнопки, чтобы не оценить ещё раз.
    await callback.message.edit_text(texts.FEEDBACK_THANKS, parse_mode="HTML")
    await callback.answer(texts.TOAST_FEEDBACK_RECORDED)
