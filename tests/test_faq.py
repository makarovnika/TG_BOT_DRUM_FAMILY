"""Тесты для FAQ-карусели (ТЗ §8.10).

Покрытие:
- show_faq_list — отправляет список вопросов;
- faq_open_item — открывает конкретную карточку и шлёт edit_text;
- faq_open_item на неизвестный id — отвечает alert, не падает;
- faq_back_to_list — возвращает к списку.
"""

from unittest.mock import AsyncMock, MagicMock

from src.bot.faq_data import FAQ_ITEMS, get_faq_item
from src.bot.handlers.faq import (
    FAQ_INTRO,
    faq_back_to_list,
    faq_open_item,
    show_faq_list,
)


def _msg() -> MagicMock:
    m = MagicMock()
    m.answer = AsyncMock()
    return m


def _cb(data: str | None = None) -> MagicMock:
    cb = MagicMock()
    cb.data = data
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


async def test_show_faq_list_sends_intro_with_questions() -> None:
    msg = _msg()
    await show_faq_list(msg)
    msg.answer.assert_awaited_once()
    call = msg.answer.call_args
    assert call.args[0] == FAQ_INTRO
    # клавиатура присутствует
    assert call.kwargs.get("reply_markup") is not None
    # парс-режим включён, потому что в FAQ_INTRO есть <b>
    assert call.kwargs.get("parse_mode") == "HTML"


async def test_faq_open_item_known_id() -> None:
    item = FAQ_ITEMS[0]
    cb = _cb(data=f"faq:{item.id}")

    await faq_open_item(cb)

    cb.message.edit_text.assert_awaited_once()
    text = cb.message.edit_text.call_args.args[0]
    assert item.question in text
    assert item.answer in text
    cb.answer.assert_awaited_once()


async def test_faq_open_item_unknown_id_alerts() -> None:
    """Если callback пришёл с устаревшим item_id — alert, не падение."""
    cb = _cb(data="faq:nonexistent")

    await faq_open_item(cb)

    cb.message.edit_text.assert_not_called()
    cb.answer.assert_awaited_once()
    # show_alert=True — иначе пользователь не увидит сообщение
    assert cb.answer.call_args.kwargs.get("show_alert") is True


async def test_faq_back_to_list_returns_intro() -> None:
    cb = _cb(data="faq:_back")
    await faq_back_to_list(cb)
    cb.message.edit_text.assert_awaited_once()
    assert cb.message.edit_text.call_args.args[0] == FAQ_INTRO


async def test_get_faq_item_returns_none_for_unknown() -> None:
    assert get_faq_item("nope") is None


async def test_get_faq_item_returns_known() -> None:
    item = get_faq_item(FAQ_ITEMS[0].id)
    assert item is not None
    assert item.id == FAQ_ITEMS[0].id


def test_all_faq_ids_unique() -> None:
    """Защита от дубликатов id в FAQ_ITEMS — это сломает навигацию."""
    ids = [item.id for item in FAQ_ITEMS]
    assert len(ids) == len(set(ids)), f"Дубликаты id в FAQ_ITEMS: {ids}"


def test_all_faq_ids_safe_for_callback_data() -> None:
    """ID должен влезать в callback_data (лимит 64 байта) с префиксом faq:."""
    for item in FAQ_ITEMS:
        full = f"faq:{item.id}".encode()
        assert len(full) <= 64, f"id `{item.id}` слишком длинный для callback_data"
        # И не содержит двоеточий — иначе сломается split(":", 1)
        assert ":" not in item.id, f"id `{item.id}` содержит двоеточие"
