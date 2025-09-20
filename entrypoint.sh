#!/bin/bash
set -e

if [ "$1" = "migrate" ]; then
  echo "Running Alembic migrations..."
  alembic upgrade head
  exit 0
fi

echo "Starting Uvicorn server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
