# Progress Log

## Current Verified State

- Repository root: `/Users/muraveika/Телеграм`
- Standard startup path: `./init.sh`
- Standard verification path: `uv run pytest -q` + `uv run ruff check src tests`
  (внутри `./init.sh`), плюс `pre-commit` hook в `.githooks/pre-commit`.
- Git: ветка `main`, ~30 коммитов на `origin/main`, push настроен через keychain.
- Tests: **91 зелёных** (smoke, db, yclients-client, user_service, handlers,
  middleware, booking, static_info, assets, fallback).
- Passing features (7 из 8 MVP + 1 design): `setup-000`, `yclients-001`,
  `registration-002`, `booking-individual-003`, `my-bookings-004`,
  `profile-005`, `brand-ui-008`.
- Not started: `booking-group-006` (групповых занятий у школы нет — проверено
  smoke).
- Partial: `deploy-007` (Docker готов, на VPS не разворачивали).
- Закрытые открытые вопросы:
  - SMS-подтверждение `book_record` НЕ требуется.
  - Email обязателен в `book_record` для Drum Family.
  - Правильный endpoint отмены — `DELETE /record/{cid}/{id}` (singular).
- Оставшиеся открытые вопросы:
  - У услуг школы `duration=0` — не понятно, откуда брать длительность.
  - У школы нет рабочего endpoint'а абонементов (`/loyalty/abonements` → 404).
  - Phase 2 ТЗ (напоминания 24/1ч, обратная связь, Mini App) — отдельные фичи.

## Session Log

### Session 010 — критический аудит после Phase 1 (2026-05-20)

- Goal: пройти критическим взглядом по результату Phase 1, починить найденное.
- Found / fixed:
  - **🔴 assert в client.py:288** (рецидив старого #3) — заменён на raise.
    Стрипался под `python -O`.
  - **🟡 Dead code в profile.py** — `@router.message(F.text == MENU_PROFILE)`
    никогда не срабатывал после Phase 1 (кнопка убрана из меню). Убрал
    Router и декоратор; функция `show_profile` теперь вызывается только
    из `commands.cmd_profile`. main.py не подключает profile.router.
  - **🟡 Legacy константы** в main_menu.py (MENU_CANCEL/PROFILE/ABOUT) — удалены.
  - **🟡 Inline-строки в callback.answer** (4 шт) — вынесены в `texts.py`
    как `TOAST_*` константы.
  - **🟡 ТЗ §9.4** — на «📍 Адрес» добавлены 3 URL-кнопки: Карта (2GIS),
    Позвонить (`tel:+79952928103`), Админ (`@Drum_Family_admin`).
  - **🟡 ТЗ §9.5** — после подтверждения записи добавлены 2 кнопки:
    «✕ Отменить» (использует CANCEL_PREFIX из bookings.py) и
    «🗺 Маршрут на карте». Под `/admin` тоже добавлена URL-кнопка.
  - **🟡 Нет тестов на assets.banner()** — добавил 4 теста в tests/test_assets.py.
  - **🟡 Tracking-файлы расходились с реальностью** — feature_list.json
    получил новую фичу `brand-ui-008` (passing) с evidence, claude-progress.md
    Session 009 и 010, quality-document.md актуализирован.
- Verification run: `uv run pytest -q` — 87 → 91 (+4 на banner).
- Files / commits: текущий коммит этой сессии.
- Known risk: file_id-кэш для баннеров не сделан (премий-оптимизация),
  Markdown V2 не реализован (HTML работает визуально так же).

### Session 009 — Phase 1 ТЗ Drum Family (брендовый рестайл, 2026-05-19→20)

- Goal: применить ТЗ дизайн-команды (`drum-family-bot-tz.md`) к боту —
  тексты, меню, ассеты, BotFather-инструкция.
- Completed:
  - **texts.py** — централизация всех сообщений с брендовым тоном,
    1-2 эмодзи, ≤8 строк, эмодзи только из гайда §10.
  - **Новое меню** (ТЗ §9.1): 🥁 Пробный / 📅 Расписание / 💳 Стоимость /
    📍 Адрес / ❓ FAQ / 💬 Админ. Старое (Профиль/Отменить/О школе) убрано.
  - **static_info.py** — 4 новых handler'а на статические разделы
    (Адрес/Стоимость/FAQ/Админ), каждый доступен через кнопку И через
    /команду.
  - **commands.py** — добавлены алиасы /trial /schedule /profile /contacts
    /prices /faq /admin.
  - **main.py** — `set_my_commands` обновлён до 10 команд из ТЗ §7.
  - **SVG-исходники** (`assets/source/`) + `build.sh` (rsvg-convert) +
    `assets/README.md`.
  - **Готовые PNG** скопированы из outputs/ (cairosvg-сборка, все < 90 КБ).
  - **bot/assets.py** — функция `banner(name)` → FSInputFile.
  - **Подключение баннеров** в 4 handler'а: welcome → /start (новый юзер),
    trial → start_booking, contacts → show_contacts, schedule →
    show_my_bookings.
  - **edit_text → edit_caption** во всех 5 шагах booking-FSM (потому
    что первое сообщение теперь photo).
  - **botfather/botfather-setup.md** — пошаговая инструкция: аватар,
    Bio, About, /setcommands.
- Verification run: `uv run pytest -q` — 60 → 87 (+5 на static_info,
  +2 на fallback, +7 на booking handlers, обновлены 7 существующих
  под answer_photo/edit_caption).
- Files / commits: `783b447`, `580c4a6`, `23feda6`.
- Known risk:
  - Аватар и текст bio/about в @BotFather пока не установлены (это
    действия Никиты вручную).
  - HTML вместо MarkdownV2 (визуально то же, формально расходится с ТЗ).

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
