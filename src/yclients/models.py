"""Pydantic-модели ответов YClients.

ВАЖНО: эти модели написаны по документации (developers.yclients.com,
yclients.docs.apiary.io) без проверки против реального API. После получения
партнёрского токена нужно прогнать `src/yclients/smoke_test.py` против
реальной школы и поправить расхождения (см. notes у фичи yclients-001).

`extra="ignore"` — YClients присылает много полей, нам нужны не все;
неизвестные поля молча отбрасываются.
"""

from pydantic import BaseModel, ConfigDict, Field


class YClientsModel(BaseModel):
    """Общая конфигурация для всех моделей."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class AuthResponse(YClientsModel):
    """Ответ POST /auth."""

    id: int
    user_token: str
    name: str | None = None
    phone: str | None = None
    email: str | None = None


class Service(YClientsModel):
    """Услуга из GET /book_services/{company_id}."""

    id: int
    title: str
    category_id: int | None = None
    price_min: int | float | None = None
    price_max: int | float | None = None
    duration: int | None = None  # в секундах
    comment: str | None = None


class Staff(YClientsModel):
    """Преподаватель из GET /book_staff/{company_id}."""

    id: int
    name: str
    specialization: str | None = None
    avatar: str | None = None
    rating: float | None = None


class Client(YClientsModel):
    """Клиент из GET/POST /clients/{company_id}."""

    id: int
    name: str
    phone: str
    email: str | None = None
    # В YClients у клиента бывает много полей (sex, birth_date, …) — добавим по мере надобности.


class Slot(YClientsModel):
    """Слот времени из GET /book_times/{company_id}/{staff_id}/{date}."""

    # YClients возвращает время как unix timestamp И как ISO-строку, выберем то, что есть.
    datetime: str | None = None  # ISO-строка
    time: str | None = None  # "10:00"
    seance_length: int | None = None  # длительность в секундах


class BookRecord(YClientsModel):
    """Ответ POST /book_record/{company_id}."""

    id: int
    hash: str | None = None
    # Реальный ответ содержит больше полей; модель расширим после smoke-теста.


class Record(YClientsModel):
    """Существующая запись из GET /records/{company_id}."""

    id: int
    services: list[Service] = Field(default_factory=list)
    staff: Staff | None = None
    date: str | None = None  # "2026-05-20 10:00:00"
    seance_length: int | None = None
    visit_attendance: int | None = None  # 0 — ждём, 1 — пришёл, -1 — не пришёл
