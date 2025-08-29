# Base: Debian bookworm slim, Python 3.10
FROM python:3.10-slim

# -------- Runtime env --------
# Prevent Python from writing .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

# -------- System deps --------
# NOTE: Include build-essential for compiling wheels (e.g., psycopg2), and libpq-dev for Postgres client libs.
# If you only use SQLite, libpq-dev can be removed.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential \
      gcc \
      libpq-dev \
      curl \
 && rm -rf /var/lib/apt/lists/*

# -------- Python deps --------
# Tip: keep pip up-to-date; use --no-cache-dir to reduce layer size.
COPY requirements.txt ${APP_HOME}/
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# -------- App code --------
COPY . ${APP_HOME}/

# -------- Static/Migrate --------
# IMPORTANT:
# Do NOT run collectstatic/migrate at build time.
# They depend on environment (.env, secrets) and should be executed at deploy/runtime via:
#   docker compose run --rm web python manage.py migrate --noinput
#   docker compose run --rm web python manage.py collectstatic --noinput

# -------- Network --------
EXPOSE 8000

# -------- Entrypoint --------
# Use Gunicorn to serve Django WSGI app.
CMD ["gunicorn", "paragourmet.wsgi:application", "--bind", "0.0.0.0:8000"]
