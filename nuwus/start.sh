#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

DB_FILE="${DB_SQLITE_PATH:-db.sqlite3}"
mkdir -p "$(dirname "$DB_FILE")" "${MEDIA_DIR:-media}"

# data awal hanya diisi saat database belum pernah dibuat
BARU=0
if [ "${DB_ENGINE:-mysql}" = "sqlite" ] && [ ! -f "$DB_FILE" ]; then
    BARU=1
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "$BARU" = "1" ]; then
    python manage.py seed_nuwus --password "${ADMIN_PASSWORD:-nuwus12345}"
fi

exec gunicorn nuwus_api.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WORKERS:-2}
