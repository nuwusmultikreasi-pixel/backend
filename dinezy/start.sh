#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
[ -f .env ] || cp .env.example .env
export PYTHONPATH="$PWD/backend:${PYTHONPATH}"
python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec gunicorn config.wsgi:application --pythonpath "$PWD/backend" --preload --bind 0.0.0.0:${PORT:-8000} --workers ${WORKERS:-3}
