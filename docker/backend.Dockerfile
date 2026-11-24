FROM python:3.11-slim AS base

RUN groupadd -r sentryflow && useradd -r -g sentryflow -s /bin/false sentryflow

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir . \
    && pip install --no-cache-dir aiosqlite

COPY backend/ backend/
COPY data/ data/
COPY attacks/ attacks/
COPY tests/ tests/

RUN chown -R sentryflow:sentryflow /app
USER sentryflow

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
