"""Smoke-тест против реального YClients API.

Запускается ВРУЧНУЮ:

    uv run python -m src.yclients.smoke_test

Все запросы — read-only Booking API:
- auth (только в legacy-режиме);
- get_services;
- get_staff;
- get_book_dates для первого преподавателя на ближайшие 2 недели;
- get_book_times для первой свободной даты этого преподавателя.

Ничего не создаёт. POST /book_record намеренно НЕ дёргается — он создаст
реальную запись в школьном расписании.
"""

import asyncio
from datetime import date, timedelta

from src.config import get_settings
from src.yclients.client import YClientsClient


async def main() -> None:
    s = get_settings()

    if not s.yclients_partner_token:
        raise SystemExit(
            "В .env пустой YCLIENTS_PARTNER_TOKEN — некуда стучаться. "
            "Сначала получи партнёрский токен на developers.yclients.com "
            "(вкладка «Общая информация»)."
        )

    # Выбираем режим аутентификации по тому, что есть в .env.
    if s.yclients_user_token:
        print("==> mode: статический User Token (из «Доступ к API»)")
        client_kwargs = {"user_token": s.yclients_user_token}
    elif s.yclients_user_login and s.yclients_user_password:
        print("==> mode: логин/пароль админа (POST /auth)")
        client_kwargs = {
            "user_login": s.yclients_user_login,
            "user_password": s.yclients_user_password,
        }
    else:
        raise SystemExit(
            "В .env нет ни YCLIENTS_USER_TOKEN, ни пары YCLIENTS_USER_LOGIN + "
            "YCLIENTS_USER_PASSWORD. Заполни одно из двух."
        )

    async with YClientsClient(
        partner_token=s.yclients_partner_token,
        company_id=s.yclients_company_id,
        **client_kwargs,
    ) as yc:
        # auth() имеет смысл только в legacy-режиме; для статического — пропускаем.
        if s.yclients_user_login:
            await yc.auth()
            print("==> auth OK")

        services = await yc.get_services()
        print(f"\n==> services ({len(services)}):")
        for svc in services:
            duration_min = (svc.duration or 0) // 60
            print(f"   - [{svc.id:>6}] {svc.title} ({duration_min} мин)")

        staff = await yc.get_staff()
        print(f"\n==> staff ({len(staff)}):")
        for member in staff:
            print(f"   - [{member.id:>6}] {member.name}: {member.specialization or '-'}")

        # Берём первого преподавателя и смотрим, на какие даты можно записаться
        # в ближайшие 2 недели.
        if not staff:
            print("\n==> нет преподавателей — пропускаем dates/times")
            return
        first_staff = staff[0]
        today = date.today()
        date_from = today.isoformat()
        date_to = (today + timedelta(days=14)).isoformat()

        dates = await yc.get_book_dates(
            staff_id=first_staff.id,
            date_from=date_from,
            date_to=date_to,
        )
        print(
            f"\n==> book_dates для {first_staff.name} ({date_from}..{date_to}):"
            f"\n   booking_dates ({len(dates.booking_dates)}): {dates.booking_dates[:10]}"
            f"\n   working_dates ({len(dates.working_dates)}): {dates.working_dates[:10]}"
        )

        # И слоты на первую доступную дату.
        if not dates.booking_dates:
            print("\n==> нет дат для записи — пропускаем slots")
            return
        first_date = dates.booking_dates[0]
        slots = await yc.get_book_times(staff_id=first_staff.id, date=first_date)
        print(f"\n==> book_times для {first_staff.name} {first_date} ({len(slots)} слотов):")
        for slot in slots[:5]:
            print(f"   - {slot.time}  (datetime: {slot.datetime})")
        if len(slots) > 5:
            print(f"   ... и ещё {len(slots) - 5}")

    print("\n==> smoke OK (book_record намеренно не дёргали — он создаёт реальную запись)")


if __name__ == "__main__":
    asyncio.run(main())
