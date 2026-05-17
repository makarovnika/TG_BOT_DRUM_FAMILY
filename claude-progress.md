# Progress Log

## Current Verified State

- Repository root: `/Users/muraveika/Телеграм`
- Standard startup path: `./init.sh`
- Standard verification path: `uv run pytest -q` + `uv run ruff check src tests`
  (внутри `./init.sh`), плюс `pre-commit` hook в `.githooks/pre-commit`.
- Git: ветка `main`, 20 коммитов (последний — `209419c`).
- Tests: **83 зелёных** (smoke, db, yclients-client, user_service, handlers, middleware, booking).
- Passing features (4 из 8 MVP): `setup-000`, `yclients-001`, `registration-002`, `profile-005`.
- In-progress: `booking-individual-003` (UI готов, реальная запись с email-фиксом
  не проверена), `my-bookings-004` (UI готов, реальная отмена не проверена).
- Not started: `booking-group-006` (групповые занятия).
- Partial: `deploy-007` (Docker готов, на VPS не разворачивали).
- Закрытые открытые вопросы:
  - SMS-подтверждение `book_record` НЕ требуется (резолв 2026-05-17 23:49).
  - Email обязателен в `book_record` для Drum Family (резолв 2026-05-17 23:49).
- Оставшиеся открытые вопросы:
  - DELETE-endpoint отмены записи (`/records/{cid}/{id}`) не проверен на реальной записи.
  - У услуг школы `duration=0` — не понятно, откуда брать длительность.
  - У школы нет рабочего endpoint'а абонементов (`/loyalty/abonements` → 404).

## Session Log

### Session 008 — booking-individual-003 в почти passing (2026-05-17→18)

- Goal: реализовать FSM записи на занятие + закрыть оставшиеся пункты
  предыдущего аудита.
- Completed:
  - **FSM записи**: src/bot/states/booking.py (5 состояний), keyboards/booking.py
    (inline-клавиатуры с локализованными датами), handlers/booking.py
    (entry + 4 шага FSM + confirm + cancel + catch-all). Услуги/тренеры
    кэшируются в FSM-data (закрытие пункта #6 предыдущего аудита).
  - **YClientsClient.get_staff(service_ids=...)**: добавлен фильтр,
    чтобы показывать только релевантных тренеров (не админов/аренду).
  - **Новый аудит (8 пунктов)**: общий escape_html в utils.py, типизация
    `Client`, /help без «(скоро будет)», cancel_declined восстанавливает
    кнопку, catch-all в booking FSM, None-checks для callback.message и
    callback.data, +7 тестов на booking handlers. Коммит `9719103`.
  - **Реальный тест записи в Telegram (2026-05-17 23:49)**:
    YClients вернул 422 «Не передан обязательный параметр email».
    SMS-подтверждение НЕ требуется (это и есть резолв открытого вопроса
    #14). Email обязателен.
  - **Реальный тест UI (Вариант A, 2026-05-18 00:03)**: флоу
    услуга→тренер→дата→слот→summary→«↩️ Отмена» работает, никакой
    записи в YClients не создаётся.
  - **Фикс email**: confirm_booking тянет get_client_by_id перед
    book_record и передаёт email из карточки YClients (коммит `209419c`).
- Verification run:
  - `uv run pytest -q` — 83 passed (76 → 83);
  - Реальный flow в Telegram пройден для всех шагов кроме финального
    «✅ Записаться с email-фиксом».
- Files / commits:
  - новые: `src/bot/states/booking.py`, `src/bot/keyboards/booking.py`,
    `src/bot/handlers/booking.py`, `src/bot/utils.py`,
    `evidence/profile-005.md`;
  - коммиты: `f901fdc` (booking FSM), `9719103` (новый аудит), `209419c`
    (email fix).
- Known risk / unresolved:
  - **`booking-individual-003` НЕ закрыта в passing** — реальная запись
    с email-фиксом не проверена. Остановились перед интерактивным тестом
    по решению Никиты.
  - **`my-bookings-004` тоже не закрыта** — UI работает, но реальная
    отмена через DELETE /records/{cid}/{id} не проверена. Если endpoint
    окажется неправильным, бот покажет «Не получилось отменить» (обработка
    есть).
- Next best step (см. session-handoff.md):
  1. Запустить бота, пройти полный booking-флоу до «✅ Записаться» —
     убедиться, что запись создаётся в YClients.
  2. Затем «📅 Мои занятия» → найти эту новую запись → отменить через
     бота. Проверим оба сценария за один тест.

### Session 007 — registration passing + profile + my-bookings (2026-05-17)

- Goal: закрыть registration-002 и сразу сделать profile-005, my-bookings-004.
- Completed:
  - registration-002 → `passing` (Никита прошёл /start → имя → телефон →
    «Отлично, ты зарегистрирован» + меню; в SQLite сохранилась корректная
    связка telegram_id ↔ yclients_client_id);
  - profile-005 → `passing` (Никита нажал «Мой профиль», получил карточку
    с реальными данными: 38 посещений, баланс −3500 ₽);
  - my-bookings-004 → in_progress (UI готов, реальная отмена не проверена);
  - попутно расширены Client и Record модели на основе реальных
    YClients-ответов (поля surname, display_name, visits, spent, paid,
    balance, datetime/length у Record);
  - DepsMiddleware инжектит yclients-клиент напрямую (раньше только через
    UserService);
  - 60 → 77 тестов.
- Files / commits: `c257a73` (registration close + profile + my-bookings).

### Session 006 — критический аудит + точечные фиксы (2026-05-17)

- Goal: Никита попросил «отнестись ко всему критически» — провести аудит
  и поправить найденное.
- Completed:
  - Аудит проведён, 28 пунктов разной серьёзности зафиксированы в ответе.
  - **Wave 1** (баги конфига/клиента/инфры, коммит `854a85a`):
    - `init.sh`: printf-баг с лишними пробелами в startup команде;
    - `client.py`: убран `assert last_exception` (стрипается под -O);
      переименован `auth_retries_left` → `already_refreshed` с честным
      комментарием про retry-бюджет;
    - `config.py`: `extra="forbid"` ловит опечатки в env-переменных;
    - `normalize_phone`: `[^0-9]` вместо `\D` (юникод-цифры больше не проходят);
      граница 10..15 → 11..15;
    - Dockerfile uv `0.4` → `0.11` (синхронизация с локальным lock-форматом);
    - docker-compose: добавлен healthcheck;
    - `.python-version=3.11`, `data/.gitkeep`;
    - +3 теста на normalize_phone (буквы, юникод-цифры, короткое РФ).
  - **Wave 2-4** (UX-улучшения + тесты на handlers, коммит `23ab4e6`):
    - catch-all обработчики в FSM регистрации (не-текстовые сообщения);
    - `handlers/commands.py`: `/cancel`, `/help`;
    - `menu_stub.py`: индивидуальные описания вместо общего «в разработке»;
    - +18 тестов на handlers (start, регистрация, cancel, help, stubs);
    - +3 теста на DepsMiddleware.
  - **Wave 5** (этот коммит):
    - `quality-document.md`: оценки приведены к реальности — handlers
      D → B, services D → B, middlewares новый слой A, Docker C.
    - `evidence/setup-000.md` и `evidence/yclients-001.md` —
      заполненные рубрики задним числом, чтобы шаблон не был «призраком».
    - `claude-progress.md`: сессии 001-004 сжаты в archive-блок.
  - **Сторонний эффект**: из `.env` удалена строка `USE_MOCK_YCLIENTS=true`
    (leftover, чтобы Settings с `extra="forbid"` стартовал).
- Verification run: `uv run pytest -q` — 60 passed; pre-commit на каждом
  коммите Wave 1 и Wave 2-4.
- Evidence captured: см. evidence/*.md, рубрики 12/12 и 11/12.
- Commits: `854a85a`, `23ab4e6` + этот коммит.
- Known risk or unresolved issue:
  - registration-002 всё ещё blocked на 403 (Admin API не доступен с
    статическим user_token);
  - Dockerfile не проверен локально — деплой на VPS будет первым реальным запуском.
- Next best step: ждём от Никиты решения по разблокировке Admin API
  (вариант B: login/password в `.env`). Без этого `registration-002` не сдвинется.

### Session 005 — закрытие yclients-001 в passing (2026-05-17)

- Goal: smoke против реального YClients API.
- Completed: получены partner+user токены, заполнен `.env`, smoke прошёл
  (4 услуги + 6 преподавателей школы), добавлены 5 тестов на статический
  режим, поправлена опечатка `CLIENTS_COMPANY_ID` → `YCLIENTS_COMPANY_ID`.
- Verification: smoke зелёный, 25 тестов pytest.
- Commits: `a99df69` (static-token support), `1e2b4ba` (docs).
- Next best step: `registration-002`.

## Archive (sessions 001-004)

Сжатые сводки. Полные детали — в git log конкретных коммитов.

- **Session 001** (шаблоны walkinglabs) — созданы `CLAUDE.md`, `AGENTS.md`,
  `init.sh`, `feature_list.json`, остальные tracking-файлы. Кода ещё нет.
- **Session 002** (каркас, `0255469`) — `uv init`, зависимости (aiogram/httpx/
  sqlalchemy[asyncio]/pydantic-settings/structlog/ruff/pytest), `src/main.py`
  с минимальной командой `/start`, smoke-тесты, `pyproject.toml` с
  `[tool.uv] package = false` и `pythonpath = ["."]` для pytest.
- **Session 003** (закрытие `setup-000`) — Никита заполнил `BOT_TOKEN`,
  preflight `bot.get_me()` показал @DrumFamily_Tomsk_Bot, /start реально
  отработал в Telegram, скриншот добавлен в evidence.
- **Session 004** (параллельная работа, коммиты `0255469` → `c276909`) —
  `git init -b main`, `.githooks/pre-commit` с ruff+format+pytest, DB-слой
  (`src/db/models.py` + `session.py` + 6 тестов), YClients-клиент с
  retry/refresh + 13 тестов на respx-моках, `smoke_test.py`.
