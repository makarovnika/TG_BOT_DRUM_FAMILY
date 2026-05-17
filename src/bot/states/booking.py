"""FSM-состояния записи на индивидуальное занятие.

Поток: услуга → преподаватель → дата → слот → подтверждение → API.
Каждое состояние хранит в FSM-data накопленный выбор (service_id, staff_id, …)
чтобы на шаге подтверждения собрать appointments для book_record.
"""

from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    choosing_service = State()
    choosing_staff = State()
    choosing_date = State()
    choosing_slot = State()
    confirming = State()
