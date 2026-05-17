"""Утилиты для UI бота."""


def escape_html(value: str | None) -> str:
    """Минимальный HTML-escape для Telegram.

    Telegram принимает только три спецсимвола в `parse_mode="HTML"`:
    `<`, `>`, `&`. Остальное (например, `'` или `"`) экранировать не нужно
    и даже вредно — Telegram отобразит как `&quot;` буквально.
    """
    if value is None:
        return ""
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
