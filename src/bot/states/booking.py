"""FSM-состояния записи на индивидуальное занятие.

Поток: возраст → услуга → преподаватель → дата → слот → подтверждение → API.
Каждое состояние хранит в FSM-data накопленный выбор (age_group, service_id,
staff_id, …) чтобы на шаге подтверждения собрать appointments для book_record.

ТЗ §9.2: первый шаг — выбор возрастной группы. Это нужно школе для
сортировки трафика (детское направление vs взрослое) и для дальнейшего
подбора программы. На уровне YClients API возраст НЕ передаётся — поле
appointments.services + staff_id не знают про возраст. Но мы логируем
выбор в booking.created для аналитики и можем добавить в комментарий к
записи.
"""

from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    choosing_age = State()
    choosing_service = State()
    choosing_staff = State()
    choosing_date = State()
    choosing_slot = State()
    confirming = State()
