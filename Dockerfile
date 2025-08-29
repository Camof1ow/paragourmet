FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_ROOT_USER_ACTION=ignore \
    APP_HOME=/app

WORKDIR ${APP_HOME}

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential \
      libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ${APP_HOME}/
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . ${APP_HOME}/

EXPOSE 8000
CMD ["gunicorn", "paragourmet.wsgi:application", "--bind", "0.0.0.0:8000"]
