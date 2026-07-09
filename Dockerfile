# cybercity-data — сборка артефактов города + broker producer (city.build.completed)
# Python 3.12, установка через uv из pyproject.toml, entrypoint — CLI cybercity-data
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# системные зависимости для сборки wheel-пакетов (минимально)
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
    && rm -rf /var/lib/apt/lists/*

# uv для детерминированной установки из pyproject.toml/uv.lock
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /usr/local/bin/

WORKDIR /app

# сначала манифесты (кэш слоёв), потом исходники
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY organizations/ ./organizations/

# установка проекта (editable не нужен для runtime; ставим как пакет)
RUN uv sync --frozen --no-dev --no-install-project || uv pip install --system .

# точка монтирования артефактов; runtime пишет сюда
RUN mkdir -p /app/build
VOLUME ["/app/build"]

# CLI: cybercity-data (build публикует city.build.completed после Phase 2)
ENTRYPOINT ["cybercity-data"]
CMD ["build", ".", "--out", "/app/build"]