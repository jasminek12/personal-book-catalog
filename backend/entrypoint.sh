#!/bin/sh
set -e
echo "Waiting for database..."
until python3 -c "
import sys, time
import psycopg2
from app.core.config import settings
try:
    psycopg2.connect(settings.database_url)
except Exception as e:
    print(e)
    sys.exit(1)
"; do
  sleep 1
done
echo "Database is ready."
echo "Running migrations..."
alembic upgrade head
echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
