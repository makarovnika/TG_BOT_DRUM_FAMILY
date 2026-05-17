# Progress Log

## Current Verified State

- Repository root: `/Users/muraveika/Телеграм`
- Standard startup path: `./init.sh`
- Standard verification path: `uv run pytest -q` + `uv run ruff check src tests`
  (внутри `./init.sh`), плюс `pre-commit` hook в `.githooks/pre-commit`.
- Git: репозиторий инициализирован, ветка `main`, 6 коммитов
  (`0255469` initial → `9fe2009` db → `0c71139` yclients → `c276909` docs →
  `a99df69` static-token → smoke OK).
- Last passing feature: `yclients-001` — клиент работает против реального API
  школы Drum Family Томск (4 услуги, 6 преподавателей), 25 тестов зелёные.
- Current highest-priority unfinished feature: `registration-002` — старт.
- Current blocker: нет.
- Известное ограничение: вопрос про SMS-подтверждение `book_record` для
  `booking-individual-003` всё ещё открыт (нужно к фиче 3, не блокирует фичу 2).

## Session Log

### Session 001 — каркас и шаблоны

- Date: 2026-05-17
- Goal: Завести структуру проекта по шаблону walkinglabs/learn-harness-engineering
  и подготовить базу для разработки бота.
- Completed: Созданы файлы `CLAUDE.md`, `AGENTS.md`, `init.sh`, `claude-progress.md`,
  `feature_list.json`, `session-handoff.md`, `clean-state-checklist.md`,
  `evaluator-rubric.md`, `quality-document.md`.
- Verification run: нет (Python-проект ещё не инициализирован).
- Evidence captured: список созданных файлов (см. выше).
- Commits: —
- Files or artifacts updated: 9 файлов шаблона.
- Known risk or unresolved issue:
  - не получены `BOT_TOKEN`, `YCLIENTS_PARTNER_TOKEN`, `YCLIENTS_USER_LOGIN/PASSWORD`,
    `YCLIENTS_COMPANY_ID`, `YCLIENTS_FORM_ID`;
  - не уточнено у поддержки YClients, можно ли отключить SMS-подтверждение для
    `book_record` через бота.
- Next best step: `setup-000` — `uv init`, добавить зависимости aiogram/httpx/
  SQLAlchemy/pydantic-settings/structlog/ruff/pytest/respx, создать `src/main.py`
  с минимальной командой `/start`, поднять локально и убедиться, что бот отвечает.

### Session 002 — каркас Python-проекта (setup-000, ЗАКРЫТО)

- Date: 2026-05-17
- Goal: Создать каркас по фиче `setup-000`: pyproject.toml, src/, tests/,
  установить зависимости через `uv sync`, добиться зелёного `./init.sh`.
- Completed:
  - установлен `uv 0.11.14` (через официальный установщик astral.sh, выполнил Никита);
  - `pyproject.toml` с aiogram, httpx, SQLAlchemy[asyncio], aiosqlite,
    pydantic-settings, structlog в основных зависимостях; pytest, pytest-asyncio,
    respx, ruff в dev;
  - `[tool.uv] package = false` + `pythonpath = ["."]` в pytest, чтобы
    тесты могли импортировать `src`;
  - `.gitignore`, `.env.example`, `README.md`;
  - `src/__init__.py`, `src/config.py` (pydantic-settings + ленивый `get_settings()`),
    `src/main.py` (aiogram-бот с одной командой `/start`);
  - пустые `__init__.py` под `src/bot/{handlers,keyboards,states,middlewares}/`,
    `src/yclients/`, `src/db/`, `src/services/`;
  - `tests/conftest.py`, `tests/test_smoke.py` (2 теста: версия Python, импорт `src`).
- Verification run:
  - `uv sync` — 36 пакетов поставлены;
  - `uv run ruff check src tests` — `All checks passed!`;
  - `uv run pytest -q` — `2 passed`;
  - `./init.sh` — отрабатывает целиком зелёно (с предупреждением про отсутствие `.env`,
    это ожидаемо).
- Evidence captured: см. `feature_list.json` → `setup-000.evidence` и логи в этой сессии.
- Commits: пока не коммитили — репозиторий ещё не инициализирован как git-проект.
- Files or artifacts updated:
  - новые: `pyproject.toml`, `.gitignore`, `.env.example`, `README.md`,
    `src/__init__.py`, `src/config.py`, `src/main.py`, 7 файлов `__init__.py`
    в подпакетах, `tests/conftest.py`, `tests/test_smoke.py`;
  - обновлены: `feature_list.json` (setup-000 → `in_progress`, evidence заполнен,
    добавлено поле `active_feature`), `claude-progress.md` (этот файл).
- Known risk or unresolved issue:
  - партнёрский токен YClients не запрошен (нужен к фиче `yclients-001`,
    рассмотрение заявки на developers.yclients.com занимает несколько дней) —
    `yclients-001` переведена в `blocked`;
  - вопрос про SMS-подтверждение `book_record` всё ещё открыт (нужен к
    `booking-individual-003`).
- Next best step:
  - `yclients-001` заблокирована до получения партнёрского токена. Пока ждём
    — Никите подать заявку на developers.yclients.com и параллельно написать
    в поддержку YClients про SMS-подтверждение `book_record`.
  - Опционально (если есть желание двигаться вперёд): инициализировать git-
    репозиторий и сделать первый коммит, добавить пре-коммит хуки с ruff
    (это не блокирует фичи и улучшает гигиену).

### Session 005 — закрытие yclients-001 в passing

- Date: 2026-05-17
- Goal: получить партнёрский+user-токены, прогнать smoke против реального API,
  закрыть `yclients-001` в `passing`.
- Completed:
  - Никита получил статический User Token системного пользователя в кабинете
    приложения YClients (вкладка «Доступ к API», права: Журнал записи 5/5,
    Форма записи 26/26, Клиентская база 20/20).
  - Никита получил партнёрский токен («Общая информация»).
  - В коде добавлена поддержка нового режима аутентификации (статический
    user_token вместо динамического через POST /auth): коммит `a99df69`.
  - Добавлены 5 тестов на статический режим — итого 25 тестов зелёные.
  - В `.env` заполнены `YCLIENTS_PARTNER_TOKEN`, `YCLIENTS_USER_TOKEN`,
    `YCLIENTS_COMPANY_ID` (была опечатка `CLIENTS_COMPANY_ID` — поправили).
  - Smoke-тест против реального API школы Drum Family Томск прошёл:
    - 4 услуги: Пробный урок (16956866), Персональная тренировка (17082316),
      Персональная со старшим (15830372), Аренда класса (17081862);
    - 6 преподавателей: Асад Шади, Татьяна Петрова, Джамлан Бомиссо,
      Влад Шоки, Арина Передумова, Администратор (Аренда класса).
  - `yclients-001` → `passing`, `active_feature` → `registration-002`.
- Verification run: `uv run python -m src.yclients.smoke_test` (зелёный),
  `uv run pytest -q` (25 passed), pre-commit hook на коммите `a99df69`.
- Evidence captured: см. `feature_list.json` → `yclients-001.evidence`.
- Commits: `a99df69` (static-token support).
- Files or artifacts updated:
  - изменены: `.env.example`, `src/config.py`, `src/yclients/client.py`,
    `src/yclients/smoke_test.py`, `tests/test_yclients_client.py`,
    `feature_list.json`, `claude-progress.md`.
- Known risk or unresolved issue:
  - в реальных ответах YClients у услуг `duration=0` — школа не заполнила;
    некритично, поле опциональное;
  - вопрос про SMS-подтверждение `book_record` всё ещё открыт (нужен к
    `booking-individual-003`, не блокирует `registration-002`).
- Next best step: начать `registration-002` — FSM (ask_name → ask_phone),
  сервис `user_service.py` поверх DB + YClients-клиента, обработчик `/start`
  с веткой «новый/уже зарегистрирован».

### Session 004 — параллельная работа пока ждём токен YClients

- Date: 2026-05-17
- Goal: пока ждём партнёрский токен, продвинуть всё, что не зависит от
  реального YClients API: git, DB-слой, YClients-клиент на respx-моках.
- Completed:
  - **Git**: `git init -b main`, `.githooks/pre-commit` (ruff check + ruff format
    --check + pytest), активирован через `git config core.hooksPath .githooks`.
    Pre-commit hook проверен — блокирует красные коммиты.
  - **3 коммита** на ветке `main`:
    - `0255469` chore: initial commit — каркас + setup-000 passing;
    - `9fe2009` feat(db): User-модель + async-фабрика сессий + 6 тестов;
    - `0c71139` feat(yclients): YClientsClient с retry/refresh + 13 тестов.
  - **DB-слой** (`src/db/`):
    - `models.py` — модель `User` (telegram_id PK BigInteger, yclients_client_id
      nullable, full_name, phone, created_at, updated_at);
    - `session.py` — `create_engine` / `create_session_factory` / `init_db`,
      принимают URL как параметр (тесты используют in-memory SQLite);
    - `tests/test_db.py` — 6 тестов (создание, апдейт, поиск, уникальность PK).
  - **YClients-клиент** (`src/yclients/`):
    - `exceptions.py` — типизированные ошибки (Auth/RateLimited/Server/Client);
    - `models.py` — pydantic-модели (AuthResponse, Service, Staff, Client,
      Slot, BookRecord, Record), `extra="ignore"`;
    - `client.py` — `YClientsClient` (async context manager, заголовок
      `Bearer {partner}, User {user}`, авторефреш user_token на 401 под
      asyncio.Lock, экспоненциальный backoff на 429/5xx с настраиваемым
      `backoff_base`, методы auth/get_services/get_staff/search_client/
      create_client);
    - `smoke_test.py` — ручной запуск против реального API после получения
      токена (`uv run python -m src.yclients.smoke_test`);
    - `tests/test_yclients_client.py` — 13 тестов на respx-моках.
- Verification run:
  - `uv run ruff check src tests` — All checks passed;
  - `uv run ruff format --check src tests` — 21 file already formatted;
  - `uv run pytest -q` — **20 passed** (2 smoke + 6 db + 12 yclients);
  - pre-commit hook отработал штатно на всех трёх коммитах.
- Evidence captured: см. `feature_list.json` → `yclients-001.evidence` и
  `registration-002.partial_progress`.
- Commits: `0255469`, `9fe2009`, `0c71139` (3 коммита на `main`).
- Files or artifacts updated:
  - новые: `.githooks/pre-commit`, `src/db/models.py`, `src/db/session.py`,
    `src/yclients/{exceptions,models,client,smoke_test}.py`,
    `tests/test_db.py`, `tests/test_yclients_client.py`;
  - обновлены: `feature_list.json`, `claude-progress.md`, `session-handoff.md`,
    `quality-document.md`, `README.md` (добавлен раздел про pre-commit).
- Known risk or unresolved issue:
  - pydantic-модели YClients написаны по документации без проверки против
    реального API — могут потребоваться правки полей после прихода токена;
  - вопрос про SMS-подтверждение `book_record` всё ещё открыт.
- Next best step:
  - Когда придёт партнёрский токен — вписать в `.env`, запустить
    `uv run python -m src.yclients.smoke_test`, поправить расхождения
    в моделях, перевести `yclients-001` в `passing`, начать `registration-002`.
  - До получения токена можно сделать ещё одну параллельную задачу:
    docker-setup для будущего деплоя (фича `deploy-007`).

### Session 003 — добивание setup-000 до passing

- Date: 2026-05-17
- Goal: подтвердить, что бот реально отвечает на `/start` в Telegram, и закрыть
  `setup-000` в `passing`.
- Completed:
  - Никита заполнил `.env` с реальным `BOT_TOKEN`;
  - preflight через `bot.get_me()` подтвердил валидность токена:
    бот @DrumFamily_Tomsk_Bot, id 8972431305, имя «Drum Family Томск»;
  - запустил бота в фоновом таске (`uv run python -m src.main`);
  - Никита отправил `/start`, получил ответ
    «Привет, Nikita! Я бот школы барабанов. Пока я умею только здороваться —
    остальное появится в следующих обновлениях.» (скриншот в чате);
  - фоновый процесс остановлен через TaskStop;
  - `setup-000` → `passing`, evidence дополнен;
  - `yclients-001` → `blocked` (партнёрский токен).
- Verification run: `bot.get_me()` + реальная отправка `/start` в Telegram.
- Evidence captured: см. `feature_list.json` → `setup-000.evidence` (последние 2 пункта).
- Commits: пока git не инициализирован.
- Files or artifacts updated: `feature_list.json`, `claude-progress.md`,
  `session-handoff.md`, `quality-document.md`.
- Known risk or unresolved issue: см. выше — токен YClients и вопрос про SMS.
- Next best step: см. выше — ждём токен YClients, опционально git init.
