#!/bin/sh

set -eu

echo "[entrypoint] startup begin"

if [ "${RUN_STARTUP_DB_PREPARE:-true}" = "true" ]; then
  echo "[entrypoint] running alembic upgrade head"
  PYTHONPATH=. alembic upgrade head

  echo "[entrypoint] seeding board categories"
  python scripts/seed_board_categories.py

  echo "[entrypoint] seeding blog categories"
  python scripts/seed_blog_categories.py

  echo "[entrypoint] verifying runtime and schema guards"
  python scripts/verify_runtime.py
  python scripts/verify_schema.py
else
  echo "[entrypoint] RUN_STARTUP_DB_PREPARE=false, skip db prepare"
fi

echo "[entrypoint] starting api"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
