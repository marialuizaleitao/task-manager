#!/bin/sh
# Entrypoint de produção: aplica migrations e coleta estáticos antes de subir
# o Gunicorn. Mantém "docker compose up -d --build" como o único comando
# necessário para atualizar a aplicação (ver docs/deploy-aws.md).
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

mkdir -p /app/logs

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-30}" \
    --keep-alive "${GUNICORN_KEEPALIVE:-5}" \
    --access-logfile /app/logs/gunicorn-access.log \
    --error-logfile /app/logs/gunicorn-error.log \
    --log-level info
