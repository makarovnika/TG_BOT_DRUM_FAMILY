# drum-school-bot

Telegram-бот для школы барабанов поверх YClients API.

> Подробный контекст, архитектура и правила работы — в [CLAUDE.md](CLAUDE.md).
> Статус фич — в [feature_list.json](feature_list.json).
> Журнал сессий — в [claude-progress.md](claude-progress.md).

## Быстрый старт

### 1. Предварительные требования

- Python 3.11+ (`python3 --version`)
- `uv` — менеджер зависимостей: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Токен бота от [@BotFather](https://t.me/BotFather)
- (Позже) Партнёрский токен YClients с developers.yclients.com

### 2. Установка

```sh
git clone <repo-url>
cd drum-school-bot
cp .env.example .env
# открой .env в редакторе и заполни BOT_TOKEN
```

### 3. Запуск

```sh
./init.sh                     # установка зависимостей + lint + тесты
RUN_START_COMMAND=1 ./init.sh # то же + сразу запускает бота
```

После запуска открой бота в Telegram и отправь `/start` — должен ответить «Привет».

### 4. Только тесты / линт

```sh
uv run pytest -q             # тесты
uv run ruff check src tests  # линт
uv run ruff format src tests # форматирование (по желанию)
```

### 5. Pre-commit hook (после клона на новой машине)

Хук в `.githooks/pre-commit` гоняет `ruff check` + `ruff format --check` + `pytest`
перед каждым коммитом. Активировать в свежесклонированном репо:

```sh
git config core.hooksPath .githooks
```

После этого попытка закоммитить красный код будет блокироваться.

## Структура

```
.
├── CLAUDE.md                  ← инструкции для агента
├── AGENTS.md                  ← операционные правила
├── README.md                  ← этот файл
├── init.sh                    ← стандартный путь старта + проверки
├── claude-progress.md         ← журнал сессий
├── feature_list.json          ← статус фич (источник правды)
├── session-handoff.md         ← заметки для следующей сессии
├── clean-state-checklist.md   ← чек-лист окончания сессии
├── evaluator-rubric.md        ← рубрика приёмки фичи
├── quality-document.md        ← снимок качества проекта
├── .githooks/                 ← pre-commit с ruff + pytest
├── pyproject.toml             ← зависимости (uv)
├── .env.example
├── .env                       ← реальные токены (НЕ коммитится)
├── src/
│   ├── main.py                ← точка входа
│   ├── config.py              ← настройки из .env
│   ├── bot/{handlers,keyboards,states,middlewares}/
│   ├── yclients/              ← async-клиент YClients
│   ├── db/                    ← SQLAlchemy-модели
│   └── services/              ← бизнес-логика
└── tests/
```

## Деплой на VPS

Будет добавлен на этапе фичи `deploy-007`. Базовая идея — `docker compose up -d`.

## Лицензия

Частный проект, без публичной лицензии.
