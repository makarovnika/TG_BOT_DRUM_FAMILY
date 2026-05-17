"""Smoke-тест против реального YClients API.

Запускается ВРУЧНУЮ после получения партнёрского токена:

    uv run python -m src.yclients.smoke_test

Делает три безопасных запроса: auth, get_services, get_staff. Ничего не создаёт
и не меняет — только читает справочники. Если падает на парсинге pydantic —
значит, реальный API отдаёт поля иначе, чем модели в `src/yclients/models.py`,
и модели надо поправить (это ожидаемая часть фичи yclients-001).
"""

import asyncio

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

    print("\n==> smoke OK")


if __name__ == "__main__":
    asyncio.run(main())
