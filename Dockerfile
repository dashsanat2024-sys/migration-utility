FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY migration_utility ./migration_utility
COPY alembic ./alembic
COPY alembic.ini ./

RUN pip install --upgrade pip && pip install .

RUN mkdir -p /app/data/landing

EXPOSE 8000

COPY docker/entrypoint-api.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "migration_utility.main:app", "--host", "0.0.0.0", "--port", "8000"]
