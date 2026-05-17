#!/usr/bin/env bash
#
# Стандартный путь старта проекта.
# Шаги: переход в корень → синк зависимостей через uv → линт+тесты → подсказка по запуску.
# Опционально (RUN_START_COMMAND=1) — сразу стартует бот.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Команды специфичны для стека: Python 3.11+, uv, ruff, pytest, aiogram.
# Если стек поменяется — обнови этот блок.
INSTALL_CMD=(uv sync)
VERIFY_CMD=(uv run pytest -q)
LINT_CMD=(uv run ruff check src tests)
START_CMD=(uv run python -m src.main)

echo "==> Working directory: $PWD"

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv не установлен. Установи: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi

if [ ! -f ".env" ]; then
  echo "WARNING: файла .env нет. Скопируй .env.example в .env и заполни токены." >&2
fi

echo "==> Sync dependencies"
"${INSTALL_CMD[@]}"

echo "==> Lint"
"${LINT_CMD[@]}"

echo "==> Baseline verification (pytest)"
"${VERIFY_CMD[@]}"

echo "==> Startup command:"
printf '    %q' "${START_CMD[@]}"
printf '\n'

if [ "${RUN_START_COMMAND:-0}" = "1" ]; then
  echo "==> Starting the bot"
  exec "${START_CMD[@]}"
fi

echo "Set RUN_START_COMMAND=1 if you want init.sh to launch the bot directly."
