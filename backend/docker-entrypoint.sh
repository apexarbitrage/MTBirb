#!/bin/sh
# Apply DB migrations, then start the API (which also serves the built PWA). Runs from the backend
# source tree so alembic finds alembic.ini + alembic/. DATABASE_URL / API keys come from the
# environment (pydantic-settings reads real env vars; no .env file is baked into the image).
set -e

# The DB may still be coming up (compose / a fresh managed instance). Retry migrations briefly.
echo "Applying database migrations (alembic upgrade head)..."
attempt=1
until alembic upgrade head; do
  if [ "$attempt" -ge 10 ]; then
    echo "Migrations failed after $attempt attempts; giving up." >&2
    exit 1
  fi
  echo "  migration attempt $attempt failed (DB not ready?); retrying in 3s..."
  attempt=$((attempt + 1))
  sleep 3
done

echo "Starting uvicorn on 0.0.0.0:8000 (WEB_CONCURRENCY=${WEB_CONCURRENCY:-2})..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${WEB_CONCURRENCY:-2}"
