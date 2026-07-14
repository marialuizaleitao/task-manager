# syntax=docker/dockerfile:1

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# --- desenvolvimento ---------------------------------------------------
FROM base AS dev

COPY backend/requirements/ requirements/
RUN pip install -r requirements/dev.txt

COPY backend/ .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# --- produção ------------------------------------------------------------
FROM base AS prod

COPY backend/requirements/ requirements/
RUN pip install -r requirements/prod.txt

COPY backend/ .

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
