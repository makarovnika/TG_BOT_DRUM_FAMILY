"""FSM-состояния для регистрации.

Поток: /start → ask_name → ask_phone → готово (главное меню).
Состояния живут в `MemoryStorage` от aiogram — при рестарте бота теряются;
для MVP это ОК.
"""

from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
