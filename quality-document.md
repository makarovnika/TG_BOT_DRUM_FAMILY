# Quality Document

Снимок качества по продуктовым доменам и архитектурным слоям. И агент, и человек
могут быстро понять, где код в хорошем состоянии, а где есть пробелы.

**Частота обновления:** после каждой значимой сессии или перед стартом новой фазы.

**Шкала оценок:**

- **A**: вся верификация зелёная, чистая архитектура, код понятен агенту, стабильные тесты
- **B**: верификация зелёная, в основном чисто, мелкие пробелы в читаемости или покрытии
- **C**: частично работает, известные пробелы, часть кода трудна для агента
- **D**: не работает или серьёзные структурные проблемы

---

## Product Domains

| Домен | Оценка | Верификация | Понятность для агента | Стабильность тестов | Ключевые пробелы | Last Updated |
|-------|--------|-------------|----------------------|---------------------|------------------|--------------|
| Регистрация ученика | A | unit + интеграционная проверка в Telegram | высокая | стабильны | — | 2026-05-18 |
| Запись на индивидуальное | B | unit (7 booking handlers), интеграция UI пройдена | высокая | стабильны | реальная запись с email-фиксом НЕ проверена; duration=0 у услуг | 2026-05-18 |
| Запись на групповое | D | — | нет кода | нет тестов | весь домен; не понятно, использует ли школа `/activity/*` | 2026-05-18 |
| Мои занятия + отмена | B | unit (3 теста) + просмотр списка проверен | высокая | стабильны | реальная отмена через DELETE НЕ проверена | 2026-05-18 |
| Профиль | A | unit (3 теста) + интеграционная проверка в Telegram (38 посещений, баланс −3500 ₽) | высокая | стабильны | абонементы (404 на /loyalty/abonements) | 2026-05-18 |

## Architectural Layers

| Слой | Оценка | Соблюдение границ | Понятность для агента | Ключевые пробелы | Last Updated |
|------|--------|-------------------|----------------------|------------------|--------------|
| Bot entry (`src/main.py`) | B | DI через middleware, корректное закрытие ресурсов в finally | высокая | нет тестов на сам main (трудно тестировать) | 2026-05-18 |
| Bot handlers (`src/bot/handlers/`) | A | 8 router'ов (start, registration, commands, profile, my_bookings, booking, menu_stub) + catch-all'ы + 30+ unit-тестов | высокая | нет интеграционных тестов (порядок include_router, фильтры F.text) | 2026-05-18 |
| FSM states (`src/bot/states/`) | A | 2 StatesGroup (registration, booking), минимум, понятны | высокая | — | 2026-05-18 |
| YClients client (`src/yclients/`) | A | 2 режима auth, retry/refresh, 32 теста на моках, smoke против реального API прошёл; Booking + Admin API; book_record с email; DELETE на singular endpoint | высокая | абонементы 404; duration=0 у услуг | 2026-05-20 |
| Texts (`src/bot/texts.py`) | A | Все строки бота в одном модуле, брендовый тон, эмодзи из гайда | высокая | 4 toast-строки тоже здесь | 2026-05-20 |
| Assets (`src/bot/assets.py` + `assets/`) | A | banner() + 4 PNG-баннера (все < 90 КБ) + аватар + SVG-исходники + build.sh; 4 теста на banner() | высокая | нет file_id-кэша (премий-оптимизация) | 2026-05-20 |
| Static info (`src/bot/handlers/static_info.py`) | A | Контакты с inline-кнопками (Карта/Звонок/Админ), Стоимость, Админ; FAQ переехал в отдельный модуль | высокая | Стоимость — placeholder, ждёт цен | 2026-05-20 |
| FAQ (`src/bot/handlers/faq.py` + `src/bot/faq_data.py`) | A | Карусель из 8 вопросов с навигацией, edit_text-переключение между списком и карточкой, 8 тестов | высокая | Контент — placeholder, ждёт текста с drumfamily.ru | 2026-05-20 |
| Banner cache (модульный в `src/bot/assets.py`) | A | После 1-й отправки PNG кэшируется file_id; повторные send_photo шлют строку. 5 тестов | высокая | Сбрасывается при рестарте (не персистится — намеренно) | 2026-05-20 |
| DB layer (`src/db/`) | A | User-модель + async-сессия + 6 тестов CRUD на in-memory SQLite | высокая | нет миграций (Alembic); схема меняется через recreate | 2026-05-18 |
| Services (`src/services/`) | B | UserService + normalize_phone + 14 тестов | высокая | сервис коммитит сам внутри register() — не unit-of-work; нет тестов на ошибочные ветки YClients | 2026-05-18 |
| Middlewares (`src/bot/middlewares/`) | A | DepsMiddleware + 3 теста (инжекция, реальный SELECT, проброс exception); инжектит yclients-клиент напрямую | высокая | — | 2026-05-18 |
| Конфиг (`src/config.py`) | A | pydantic-settings, ленивый `get_settings()`, `extra="forbid"` ловит опечатки | высокая | не покрыт тестами (значения env обычно мокаются, не сам Settings) | 2026-05-18 |
| Harness (init.sh + tests/) | A | стандартный, зелёный, 83 теста | высокая | — | 2026-05-18 |
| Git hooks (`.githooks/`) | A | pre-commit с ruff + format-check + pytest, активен | высокая | — | 2026-05-18 |
| Docker (Dockerfile + compose) | C | multi-stage, healthcheck, лимиты, volume для bot.db, .python-version=3.11 | высокая | НЕ проверено локально — деплой на VPS будет первым реальным запуском | 2026-05-18 |
| Utils (`src/bot/utils.py`) | A | общий escape_html, убраны 3 дубликата | высокая | — | 2026-05-18 |

## Change History

### 2026-05-20 — Session 011 (FAQ + file_id кэш)

- Changes: FAQ-карусель (8 вопросов, навигация по карточкам, тесты),
  file_id-кэш для баннеров (модульный синглтон).
- Domains promoted: «Профиль и абонементы» B → A не сдвинулось
  (профиль был уже A, абонементы по-прежнему 404).
- Domains demoted: —
- New gaps identified:
  - FAQ-контент остаётся placeholder — ждём текста с drumfamily.ru.
- Gaps closed:
  - «FAQ — placeholder без навигации» (был отмечен в Phase 2 remaining).
  - «file_id-кэш для баннеров не сделан» (был премий-оптимизация в аудите).

### 2026-05-20 — Sessions 009-010 (Phase 1 ТЗ Drum Family + аудит)

- Changes: брендовый рестайл по ТЗ — texts.py, новое меню (6 кнопок),
  static_info с 4 handler'ами, баннеры подключены в 4 ключевых места,
  10 команд в Telegram UI. Затем аудит и фиксы: assert→raise, dead code
  убран, inline-кнопки на «📍 Адрес» и после booking, toast'ы вынесены.
- Domains promoted:
  - новый домен `brand-ui-008` создан как passing.
- Domains demoted: —
- New gaps identified:
  - HTML вместо MarkdownV2 (некритично).
  - file_id-кэш не реализован.
  - Стоимость/FAQ — placeholder-тексты.
- Gaps closed:
  - assert-рецидив (#3 из старого аудита окончательно закрыт).
  - dead handler в profile.py.

### 2026-05-18 — Sessions 007–008 (закрытие 3 фич + крупный заход на 003)

- Changes: registration-002, profile-005 закрыты в `passing`;
  my-bookings-004 и booking-individual-003 в `in_progress` с почти
  готовым кодом, но без подтверждения реального write в YClients.
- Domains promoted: Регистрация D→A, Профиль D→A, Мои занятия D→B,
  Запись на индивидуальное D→B.
- Domains demoted: —
- New gaps identified:
  - YClients требует email для `book_record` (резолвится фиксом
    `209419c` — берём email из карточки клиента);
  - DELETE-endpoint отмены записи не проверен на реальной записи;
  - duration услуг = 0, длительность берём из seance_length слота.
- Gaps closed:
  - SMS-подтверждение `book_record` — закрыто, не требуется;
  - 403 на Admin API — закрыто переходом на legacy login/password.

### 2026-05-17 (поздний вечер) — Session 005

- Changes: добавлен статический режим аутентификации (User Token системного
  пользователя). Smoke против реального API школы Drum Family Томск прошёл —
  4 услуги, 6 преподавателей. `yclients-001` закрыт в `passing`.
- Domains promoted: —
- Domains demoted: —
- New gaps identified: услуги школы в YClients не содержат duration —
  при показе расписания нужно будет искать длительность в другом месте.
- Gaps closed: «pydantic-модели не проверены против реального API» — закрыто.

### 2026-05-17 (поздний вечер) — Session 004

- Changes: подняты git + pre-commit (hook гоняет ruff + pytest), реализован
  DB-слой (User-модель + сессия + 6 тестов) и YClients-клиент с retry/refresh
  (13 тестов на respx-моках). Всего 20 тестов зелёных.
- Domains promoted: «Регистрация ученика» осталась D (фича не сдана),
  но фундамент (DB-слой) теперь A. YClients-слой D → B.
- Domains demoted: —
- New gaps identified:
  - pydantic-модели YClients не верифицированы против реального API.
- Gaps closed:
  - «нет git-репозитория» — закрыто;
  - «нет защиты от красных коммитов» — закрыто pre-commit hook'ом;
  - «нет DB-слоя» — закрыто;
  - «нет async-клиента YClients» — закрыто (за исключением smoke против
    реального API).

### 2026-05-17 (вечер) — Session 003

- Changes: `setup-000` закрыта в `passing`, бот @DrumFamily_Tomsk_Bot реально
  отвечает на `/start`. `src/main.py` промоутится B → A.
- Domains promoted: —
- Domains demoted: —
- New gaps identified: —
- Gaps closed: «бот не проверен в Telegram» — закрыто.

### 2026-05-17 (вечер) — Session 002

- Changes: создан Python-каркас. Появились реально работающие слои: `src/main.py` (B),
  `src/config.py` (B), harness `init.sh + tests/` (A — `./init.sh` отрабатывает зелёно).
- Domains promoted: ни один продуктовый домен ещё не сдвинулся (фичи `registration-002`+
  ещё не начаты).
- Domains demoted: —
- New gaps identified: —
- Gaps closed: «нет каркаса проекта» — закрыто.

### 2026-05-17 (день) — Session 001

- Changes: создан изначальный снимок качества; все домены и слои в статусе `D`,
  потому что кода ещё нет — есть только шаблонные файлы процесса.
- Domains promoted: —
- Domains demoted: —
- New gaps identified:
  - открытый вопрос про SMS-подтверждение YClients для `book_record` (домен «Запись на индивидуальное»);
  - не выяснено, какие именно типы услуг (индивидуальные/групповые) уже заведены в YClients у школы;
  - не определён формат отображения времени слотов (локальное время школы vs Unix).
- Gaps closed: —
