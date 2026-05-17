# Progress Log

## Current Verified State

- Repository root: `/Users/muraveika/Телеграм`
- Standard startup path: `./init.sh`
- Standard verification path: `uv run pytest -q` + `uv run ruff check src tests`
  (внутри `./init.sh`), плюс `pre-commit` hook в `.githooks/pre-commit`.
- Git: ветка `main`, 10 коммитов (последний — `23ab4e6`).
- Tests: 60 зелёных (smoke, db, yclients-client, user_service, handlers, middleware).
- Last passing feature: `yclients-001` — клиент работает против реального
  Booking API школы Drum Family Томск (4 услуги, 6 преподавателей).
- Current highest-priority unfinished feature: `registration-002`.
- Current blocker: 403 от Admin API YClients на `/clients/1058417`.
  Решение — переключиться на legacy login/password (см. session-handoff.md).
- Known open question: SMS-подтверждение `book_record` (нужно к `booking-individual-003`,
  не блокирует фичу 2).

## Session Log

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
