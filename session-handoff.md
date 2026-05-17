# Session Handoff

## Verified Now

- `./init.sh` зелёный: 25 тестов проходят, ruff чист.
- Telegram-бот @DrumFamily_Tomsk_Bot отвечает на `/start`.
- YClients-клиент работает **против реального API** школы Drum Family Томск:
  - 4 услуги, 6 преподавателей подгружаются через `uv run python -m src.yclients.smoke_test`;
  - режим — статический User Token (`YCLIENTS_USER_TOKEN` в `.env`),
    partner_token — `YCLIENTS_PARTNER_TOKEN`.
- Pre-commit hook гоняет ruff + tests перед каждым коммитом.
- Git: 5 коммитов на `main`.

## Changed This Session (Session 005)

- Поддержка статического User Token в `YClientsClient` (коммит `a99df69`).
- 5 новых тестов на статический режим (итого 25).
- Smoke против реального API прошёл, `yclients-001` → `passing`.
- `active_feature` → `registration-002`.

## Broken Or Unverified

- Known defect: нет.
- Unverified path: бизнес-логика регистрации (FSM, поиск/создание клиента
  в YClients, привязка `telegram_id` ↔ `yclients_client_id`).
- Risk for the next session:
  - вопрос про SMS-подтверждение `book_record` всё ещё открыт (нужен к
    `booking-individual-003`, не блокирует фичу 2);
  - в реальных ответах YClients у услуг `duration=0` — некритично, но при
    показе расписания нужно будет проверить, есть ли длительность где-то ещё.

## Next Best Step

- **Активная фича:** `registration-002` (Регистрация ученика через FSM).
- **План реализации:**
  1. `src/services/user_service.py` — обёртка над DB + YClients-клиентом:
     `get_or_register(telegram_id, name, phone)` → ищет User в SQLite,
     если нет — ищет в YClients по phone, если нет — создаёт в YClients,
     сохраняет связку в SQLite.
  2. `src/bot/states/registration.py` — FSM-состояния `WaitingForName`,
     `WaitingForPhone`.
  3. `src/bot/handlers/start.py` — `/start`: если есть в SQLite → главное
     меню, иначе → FSM регистрации.
  4. `src/bot/handlers/registration.py` — обработчики FSM.
  5. `src/bot/keyboards/main_menu.py` — Reply-клавиатура главного меню.
  6. `src/main.py` — подключить DI: `YClientsClient` + сессии БД в middleware.
  7. Тесты: unit на `user_service` с моками, интеграционный путь FSM.
- **Что считать passing:** новый пользователь после /start проходит
  ask_name → ask_phone, в YClients появляется/находится клиент с этим
  телефоном, в SQLite появляется User с привязкой; повторный /start ведёт
  сразу в главное меню без повторного ask.

## Commands

- Startup: `./init.sh`
- Verification: `uv run pytest -q` и `uv run ruff check src tests`
- Запустить бота локально: `RUN_START_COMMAND=1 ./init.sh`
- Smoke против реального YClients: `uv run python -m src.yclients.smoke_test`
- Если `uv` не виден в новой сессии: `export PATH="$HOME/.local/bin:$PATH"`
