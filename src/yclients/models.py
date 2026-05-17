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
    """Клиент из GET /client/{company_id}/{id} или GET /clients/{company_id}.

    Поля проверены против реального API школы Drum Family Томск.
    Все необязательные с дефолтом None — школа может не заполнить.

    Денежные значения (`spent`, `paid`, `balance`) в копейках? Нет —
    в реальных ответах это рубли как int (`balance: -3500` = долг 3500 ₽).
    Отрицательный `balance` = ученик должен школе.
    """

    id: int
    name: str
    surname: str | None = None
    patronymic: str | None = None
    display_name: str | None = None
    phone: str
    email: str | None = None
    birth_date: str | None = None  # YYYY-MM-DD, может быть пустой строкой
    sex: str | None = None  # «Мужской» / «Женский» / «Неизвестно»
    importance: str | None = None
    comment: str | None = None  # внутренний комментарий администратора

    # Денежная статистика (рубли).
    visits: int | None = None
    spent: int | None = None  # всего потрачено
    paid: int | None = None  # всего оплачено
    balance: int | None = None  # spent − paid, отрицательный = долг
    discount: int | None = None  # процент персональной скидки

    last_change_date: str | None = None  # ISO с таймзоной


class BookableDates(YClientsModel):
    """Ответ GET /book_dates/{company_id}.

    Структура реального ответа YClients (проверено на школе Drum Family Томск):
    - `booking_dates`: список ISO-строк дат, на которые можно записаться;
    - `booking_days`: dict {"<номер_месяца>": [день, день, ...]} — те же дни,
      разложенные по месяцам (для отрисовки календаря);
    - `working_dates` / `working_days`: всё, что выше, но для рабочих дней
      школы (более широкий набор — рабочий день ≠ день, на который есть слоты).

    В UI бота используем `booking_dates` — это то, на что реально можно
    записаться. `*_days` храним как есть на случай, если понадобятся.
    """

    booking_dates: list[str] = Field(default_factory=list)  # "YYYY-MM-DD"
    booking_days: dict[str, list[int]] = Field(default_factory=dict)
    working_dates: list[str] = Field(default_factory=list)
    working_days: dict[str, list[int]] = Field(default_factory=dict)


class Slot(YClientsModel):
    """Слот времени из GET /book_times/{company_id}/{staff_id}/{date}.

    YClients возвращает оба представления: ISO-строку (`datetime`) и
    человекочитаемое время (`time`). В UI бота показываем `time`, но в
    `book_record` отправляем `datetime` — он однозначно идентифицирует слот.
    """

    datetime: str | None = None  # ISO-строка, "2026-05-20T10:00:00+07:00"
    time: str | None = None  # "10:00"
    seance_length: int | None = None  # длительность в секундах


class BookRecordAppointment(YClientsModel):
    """Одно посещение в теле POST /book_record (массив appointments).

    В YClients-флоу запись может содержать несколько услуг подряд, но для
    нашего MVP школы барабанов одно посещение = одна услуга у одного тренера
    в один слот.
    """

    id: int  # порядковый ID внутри запроса (обычно 1)
    services: list[int]  # ID услуг
    staff_id: int
    datetime: str  # ISO-строка, та же, что вернулась из get_book_times


class BookRecordResponse(YClientsModel):
    """Ответ POST /book_record/{company_id}.

    Реальный ответ содержит больше полей (services, staff, datetime и т. д.),
    но для бота важны id и hash — они нужны для последующей отмены
    через DELETE /user/records/{record_id}/{record_hash}.
    """

    id: int
    hash: str | None = None


class Record(YClientsModel):
    """Существующая запись из GET /records/{company_id}.

    Реальная структура (по школе Drum Family):
    - `date` — локальное время школы (YYYY-MM-DD HH:MM:SS), удобно для парсинга;
    - `datetime` — ISO с таймзоной +07:00 (Томск), однозначно;
    - `seance_length` (он же `length`) — длительность в секундах;
    - `services`/`staff` — вложенные объекты, парсятся как Service/Staff;
    - `visit_attendance`: 0=ожидается, 1=пришёл, -1=не пришёл;
    - `short_link`/`review_link` — публичные ссылки YClients на запись;
    - `id` + неявный `hash` (получаем из YClients для отмены через DELETE).

    `hash` в response /records НЕ приходит (он показывается только при
    создании записи через book_record). Для отмены существующих записей
    используем endpoint DELETE /records/{company_id}/{record_id} — с
    admin-токеном, без hash.
    """

    id: int
    services: list[Service] = Field(default_factory=list)
    staff: Staff | None = None
    date: str | None = None  # "2026-05-20 10:00:00" — локальное время
    datetime: str | None = None  # ISO с таймзоной, "2026-05-20T10:00:00+07:00"
    seance_length: int | None = None  # секунды
    length: int | None = None  # секунды; обычно равно seance_length
    visit_attendance: int | None = None  # 0/1/-1
    confirmed: int | None = None  # 1 = подтверждено
    deleted: bool = False
    comment: str | None = None
    short_link: str | None = None  # https://yc.gl/c/.../...
