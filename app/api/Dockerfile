# syntax=docker/dockerfile:1
FROM python:3.12-slim

# System deps for lxml, extruct, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libxml2-dev libxslt1-dev libffi-dev git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project code needed by API (keep this lean for cache)
COPY app /app/app
COPY packages /app/packages
COPY database /app/database

# Install Python deps
RUN python -m venv /opt/venv && . /opt/venv/bin/activate \
 && pip install --no-cache-dir fastapi "uvicorn[standard]" sqlalchemy psycopg[binary] python-dotenv \
    httpx extruct lxml readability-lxml orjson w3lib

ENV PATH="/opt/venv/bin:$PATH"

# Expose port & run dev server with reload for quick iteration
EXPOSE 8000
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
