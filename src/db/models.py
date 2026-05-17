"""SQLAlchemy-модели.

Что мы храним в SQLite:
- `User` — маппинг Telegram_ID ↔ YClients_client_id + кэш имени/телефона.
  Кэшируем имя и телефон, чтобы не дёргать YClients на каждый /profile;
  поля nullable, потому что в процессе регистрации мы их добавляем поэтапно.

Что мы НЕ храним:
- расписание, услуги, преподавателей — источник правды YClients;
- FSM-состояния — пока живут в MemoryStorage от aiogram (на MVP допустимо;
  при перезапуске бота незавершённые диалоги теряются — для 100 учеников
  это редкий и не критичный кейс).
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс всех моделей."""


class User(Base):
    __tablename__ = "users"

    # telegram_id — наш первичный ключ. Это «вход в систему»: бот видит
    # каждое сообщение с telegram_id и по нему ищет привязку к YClients.
    # BigInteger — потому что Telegram-ID может быть больше 2^31.
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # Может быть None в короткий промежуток: telegram_id уже известен,
    # а клиент в YClients ещё не найден/не создан (мы в середине ask_phone).
    yclients_client_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, default=None)

    # Кэш для /profile и форматирования сообщений. Источник правды — YClients,
    # но хранение копии экономит запросы.
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"User(telegram_id={self.telegram_id}, "
            f"yclients_client_id={self.yclients_client_id}, "
            f"full_name={self.full_name!r})"
        )
