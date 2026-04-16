# ---------------------------------------------------------------------------
# Stage 1 — install Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# gcc is a safety net for any sdist packages; pyahocorasick & psycopg ship wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY repops/ repops/

# Install everything into /install for clean copy to runtime image
RUN pip install --no-cache-dir --prefix=/install --no-warn-script-location .

# ---------------------------------------------------------------------------
# Stage 2 — runtime image
# ---------------------------------------------------------------------------
FROM python:3.12-slim

# Copy installed packages and CLI scripts from builder
COPY --from=builder /install /usr/local

# Install Playwright Chromium + all its system library dependencies
RUN playwright install --with-deps chromium

WORKDIR /app

# Alembic config and migrations (run `alembic upgrade head` at deploy time)
COPY alembic.ini ./
COPY migrations/ migrations/

# Directory for shared log file (mounted as volume in docker-compose)
RUN mkdir -p /logs

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LOG_FILE=/logs/repops.log

EXPOSE 8000

# Override CMD with ["repops-worker"] for the Celery container
CMD ["repops-api"]
