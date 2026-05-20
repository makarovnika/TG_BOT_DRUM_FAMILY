"""Обработчики FSM регистрации.

Поток:
- `waiting_for_name` принимает текст с именем (валидация: ≥ 2 символов);
- `waiting_for_phone` принимает либо контакт (Telegram-кнопка), либо
  текст с номером (валидация через `normalize_phone`);
- после успешного `UserService.register` — главное меню.
"""

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy.exc import SQLAlchemyError

from src.bot import texts
from src.bot.keyboards.contact import share_phone_kb
from src.bot.keyboards.main_menu import main_menu_kb
from src.bot.states.registration import RegistrationStates
from src.bot.utils import escape_html
from src.services.user_service import UserService, normalize_phone
from src.yclients.exceptions import YClientsError

log = structlog.get_logger("handlers.registration")

router = Router(name="registration")

# Минимальная длина имени — защита от пустых строк и опечаток вроде «.»
MIN_NAME_LENGTH = 2


@router.message(RegistrationStates.waiting_for_name, F.text)
async def got_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < MIN_NAME_LENGTH:
        await message.answer(texts.REG_NAME_TOO_SHORT)
        return

    await state.update_data(name=name)
    await message.answer(
        texts.REG_ASK_PHONE.format(name=escape_html(name)),
        parse_mode="HTML",
        reply_markup=share_phone_kb(),
    )
    await state.set_state(RegistrationStates.waiting_for_phone)


@router.message(RegistrationStates.waiting_for_phone, F.contact)
async def got_contact(
    message: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    if message.contact is None or not message.contact.phone_number:
        await message.answer(texts.REG_CONTACT_UNREADABLE)
        return
    phone = normalize_phone(message.contact.phone_number)
    await _finalize(message, state, user_service, phone)


@router.message(RegistrationStates.waiting_for_phone, F.text)
async def got_phone_text(
    message: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    phone = normalize_phone(message.text or "")
    await _finalize(message, state, user_service, phone)


async def _finalize(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    phone: str | None,
) -> None:
    if phone is None:
        await message.answer(texts.REG_PHONE_NOT_RECOGNIZED)
        return

    if message.from_user is None:
        await message.answer(texts.REG_NO_USER)
        await state.clear()
        return

    data = await state.get_data()
    name = data.get("name")
    if not name:
        await message.answer(texts.REG_STATE_LOST)
        await state.clear()
        return

    try:
        await user_service.register(
            telegram_id=message.from_user.id,
            name=name,
            phone=phone,
        )
    except YClientsError as exc:
        log.warning("registration.yclients_error", error=str(exc))
        await message.answer(texts.REG_YCLIENTS_ERROR, reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return
    except SQLAlchemyError as exc:
        log.exception("registration.db_error", error=str(exc))
        await message.answer(texts.REG_DB_ERROR, reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    await state.clear()
    await message.answer(
        texts.REG_SUCCESS.format(name=escape_html(name)),
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


# Catch-all обработчики для не-текстовых сообщений в FSM. Регистрируются
# ПОСЛЕДНИМИ — aiogram идёт по handler'ам в порядке регистрации, и эти
# срабатывают только если предыдущие F.text/F.contact не подошли. Без них
# пользователь застревал бы в FSM, если бы прислал стикер/фото/голос.


@router.message(RegistrationStates.waiting_for_name)
async def name_not_text(message: Message) -> None:
    await message.answer(texts.REG_NAME_NOT_TEXT)


@router.message(RegistrationStates.waiting_for_phone)
async def phone_not_recognized(message: Message) -> None:
    await message.answer(texts.REG_PHONE_NOT_RECOGNIZED)
