# Session Handoff

## Verified Now

- What is currently working:
  - `./init.sh` отрабатывает целиком зелёно: `uv sync` ставит 36 пакетов,
    `ruff check src tests` — All checks passed, `pytest -q` — 2 passed;
  - Telegram-бот **@DrumFamily_Tomsk_Bot** (id 8972431305) реально отвечает
    на `/start` сообщением «Привет, Nikita! Я бот школы барабанов. Пока я умею
    только здороваться — остальное появится в следующих обновлениях.»
    (скриншот зафиксирован 2026-05-17 в `setup-000.evidence`);
  - каркас в `src/`: `config.py` (pydantic-settings, ленивый `get_settings()`),
    `main.py` (aiogram-бот с одной командой `/start`);
  - все подпакеты (`src/bot/{handlers,keyboards,states,middlewares}`,
    `src/yclients`, `src/db`, `src/services`) — с пустыми `__init__.py`.
- What verification actually ran: `uv sync`, `uv run ruff check src tests`,
  `uv run pytest -q`, полный `./init.sh` без `RUN_START_COMMAND`,
  `bot.get_me()` через aiogram, реальная отправка `/start` в Telegram.

## Changed This Session

- `setup-000` → `passing` (evidence дополнен скриншотом из Telegram).
- `yclients-001` → `blocked` (партнёрский токен YClients ещё не получен).
- `active_feature` в `feature_list.json` → `null` (нет активной фичи, пока ждём).
- В `claude-progress.md` добавлена Session 003.

## Broken Or Unverified

- Known defect: нет.
- Unverified path: ничего срочного — все включённые в MVP пути либо `passing`,
  либо `blocked` по понятной внешней причине.
- Risk for the next session:
  - партнёрский токен YClients не запрошен — без него `yclients-001`
    и все зависящие от него фичи (registration-002, booking-individual-003,
    my-bookings-004, profile-005, booking-group-006) стоят;
  - открытый вопрос про SMS-подтверждение `book_record` для
    `booking-individual-003` — лучше задать поддержке YClients параллельно
    с подачей заявки, чтобы к моменту разблокировки ответ уже был на руках;
  - git ещё не инициализирован — потеря работы возможна, если что-то снесётся.

## Next Best Step

- Внешние действия Никиты (вне сессии Claude):
  1. Подать заявку на developers.yclients.com на партнёрский токен.
  2. Написать в поддержку YClients: «Можно ли при создании записи через API
     (`POST /book_record`) отключить SMS-подтверждение клиента, либо есть ли
     способ создавать запись от имени админа без `book_code`?»
- Опциональная техническая задача (можно делать прямо сейчас, не блокирует ничего):
  - `git init`, первый коммит, `.gitignore` уже на месте;
  - добавить pre-commit с `ruff format --check` + `ruff check` (защищает от
    случайных красных коммитов).
- Когда придёт партнёрский токен YClients:
  - вписать в `.env`: `YCLIENTS_PARTNER_TOKEN`, `YCLIENTS_USER_LOGIN`,
    `YCLIENTS_USER_PASSWORD`, `YCLIENTS_COMPANY_ID`, `YCLIENTS_FORM_ID`;
  - перевести `yclients-001` из `blocked` в `in_progress`;
  - начать с `src/yclients/client.py`: `auth()`, `get_services()`, `get_staff()`,
    `search_client()`, `create_client()` + pydantic-модели в `models.py`.

## Commands

- Startup: `./init.sh`
- Verification: `uv run pytest -q` и `uv run ruff check src tests`
- Запустить бота локально: `RUN_START_COMMAND=1 ./init.sh`
  (или напрямую: `uv run python -m src.main`)
- Если `uv` не виден в новой сессии: `export PATH="$HOME/.local/bin:$PATH"`
