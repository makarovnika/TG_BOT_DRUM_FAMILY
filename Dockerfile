# syntax=docker/dockerfile:1.7
#
# Multi-stage Dockerfile для drum-school-bot.
# Стадия 1 (builder): ставим uv, синхронизируем зависимости в .venv.
# Стадия 2 (runtime): минимальный образ, копируем .venv и код, запускаем бота.
# Зачем multi-stage: образ runtime получается без uv, кэшей и build-инструментов.

# ---- Стадия 1: builder ----
FROM python:3.11-slim AS builder

# uv-инсталляция через официальный образ (быстрее, чем curl|sh).
COPY --from=ghcr.io/astral-sh/uv:0.4 /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Сначала только манифесты — слой кэшируется, пока зависимости не поменяются.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Потом код. При изменениях в src/ переустановка зависимостей НЕ происходит.
COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- Стадия 2: runtime ----
FROM python:3.11-slim AS runtime

# Запускаем под непривилегированным пользователем — стандартная мера безопасности.
RUN groupadd --system bot && useradd --system --gid bot --home /app bot

WORKDIR /app

# Копируем готовый venv и код из builder-стадии.
COPY --from=builder --chown=bot:bot /app/.venv /app/.venv
COPY --from=builder --chown=bot:bot /app/src /app/src

# Делаем venv доступным без активации.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER bot

# bot.db и .env подкидываются как volume/secrets из docker-compose,
# поэтому в образ не копируются.
CMD ["python", "-m", "src.main"]
