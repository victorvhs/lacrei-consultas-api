FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=2.1.3 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1

RUN groupadd -g 1001 appuser && \
    useradd -u 1001 -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

FROM base AS builder

RUN pip install "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock* ./
RUN poetry install --only main --no-root

COPY . .

RUN poetry run python manage.py collectstatic --noinput --settings=config.settings.production || true

FROM python:3.12-slim AS runtime

RUN groupadd -g 1001 appuser && \
    useradd -u 1001 -g appuser -d /app -s /sbin/nologin appuser && \
    apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/staticfiles /app/staticfiles
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    APP_VERSION="dev"

USER appuser

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "${GUNICORN_WORKERS:-2}", \
     "--threads", "${GUNICORN_THREADS:-2}", \
     "--worker-tmp-dir", "/dev/shm", \
     "--graceful-timeout", "25", \
     "--timeout", "30"]
