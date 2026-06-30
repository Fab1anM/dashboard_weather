# syntax=docker/dockerfile:1

# Multi-stage build with Xvfb and Chromium for Raspberry Pi deployment

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY README.md ./
COPY dashboard_weather ./dashboard_weather

RUN uv sync --frozen --no-dev --no-editable

# Runtime image based on Debian bookworm-slim with Chromium/Xvfb
FROM python:3.12-slim-bookworm

WORKDIR /app

# Install system dependencies for headless browser support
RUN apt-get update && apt-get install -y \
    xvfb \
    chromium \
    chromium-driver \
    fonts-liberation \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    DASHBOARD_HOST=0.0.0.0 \
    DASHBOARD_PORT=8000 \
    DISPLAY=:99

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/dashboard_weather /app/dashboard_weather
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
