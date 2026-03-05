#!/bin/sh

set -eu

echo "[entrypoint] startup begin"

run_or_warn() {
  step="$1"
  shift
  if "$@"; then
    echo "[entrypoint] ${step}: ok"
  else
    echo "[entrypoint] ${step}: failed"
    if [ "${RUN_STARTUP_DB_PREPARE_STRICT:-false}" = "true" ]; then
      echo "[entrypoint] strict mode enabled, exiting"
      exit 1
    fi
  fi
}

if [ "${RUN_STARTUP_DB_PREPARE:-true}" = "true" ]; then
  run_or_warn "alembic upgrade" env PYTHONPATH=. alembic upgrade head
  run_or_warn "seed board categories" python scripts/seed_board_categories.py
  run_or_warn "seed blog categories" python scripts/seed_blog_categories.py
else
  echo "[entrypoint] RUN_STARTUP_DB_PREPARE=false, skip db prepare"
fi

echo "[entrypoint] starting api"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
