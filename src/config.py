"""Настройки приложения, загружаются из .env через pydantic-settings.

Почему pydantic-settings:
- читает .env автоматически,
- валидирует типы (например, YCLIENTS_COMPANY_ID должен быть числом),
- не даст стартовать боту с пустым BOT_TOKEN — упадёт с понятной ошибкой.

extra="forbid" — раньше тут было "ignore", и опечатка `CLIENTS_COMPANY_ID`
вместо `YCLIENTS_COMPANY_ID` тихо проглатывалась, а бот работал с
company_id=0 и падал на 404. Теперь незнакомые поля сразу дают
понятную ошибку валидации.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        case_sensitive=False,
    )

    # Telegram — обязательный
    bot_token: str

    # YClients — на этапе setup-000 ещё пустые, заполнятся к фиче yclients-001
    yclients_partner_token: str = ""
    # User token — два режима. Если указан yclients_user_token (статический
    # системный пользователь) — он имеет приоритет; иначе клиент будет получать
    # user_token через /auth по логину/паролю.
    yclients_user_token: str = ""
    yclients_user_login: str = ""
    yclients_user_password: str = ""
    yclients_company_id: int = 0
    yclients_form_id: int = 0

    # Прочее
    database_url: str = "sqlite+aiosqlite:///./bot.db"
    log_level: str = "INFO"
    admin_telegram_ids: str = ""

    @property
    def admin_telegram_ids_list(self) -> list[int]:
        """Парсит строку '123,456,789' в список int. Пустые значения отбрасываются."""
        if not self.admin_telegram_ids:
            return []
        return [int(x) for x in self.admin_telegram_ids.split(",") if x.strip()]


def get_settings() -> Settings:
    """Ленивый геттер настроек.

    Почему ленивый, а не settings = Settings() на уровне модуля:
    без этого `import src.config` падал бы во время тестов, если в окружении
    нет BOT_TOKEN. Геттер вызывается только когда настройки реально нужны
    (на старте бота), а тесты могут спокойно импортировать модуль.
    """
    return Settings()  # type: ignore[call-arg]
