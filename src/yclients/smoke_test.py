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
            "Сначала получи партнёрский токен на developers.yclients.com."
        )

    async with YClientsClient(
        partner_token=s.yclients_partner_token,
        user_login=s.yclients_user_login,
        user_password=s.yclients_user_password,
        company_id=s.yclients_company_id,
    ) as yc:
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
