"""Create target PostgreSQL database if it does not exist.

Usage:
  .venv/bin/python scripts/bootstrap_db.py
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings


@dataclass(frozen=True)
class DbUrlParts:
    driverless_url: str
    database_name: str
    admin_url: str


def build_db_urls(database_url: str) -> DbUrlParts:
    """Normalize DATABASE_URL and build admin URL (postgres database)."""
    normalized = database_url.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlsplit(normalized)

    database_name = parsed.path.lstrip("/")
    if not database_name:
        raise ValueError("DATABASE_URL must include a database name")

    admin_url = urlunsplit((parsed.scheme, parsed.netloc, "/postgres", parsed.query, parsed.fragment))

    return DbUrlParts(
        driverless_url=normalized,
        database_name=database_name,
        admin_url=admin_url,
    )


async def ensure_database_exists(database_url: str) -> bool:
    """Ensure target database exists.

    Returns:
      True if created, False if already existed.
    """
    parts = build_db_urls(database_url)

    conn = await asyncpg.connect(parts.admin_url)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            parts.database_name,
        )

        if exists:
            return False

        await conn.execute(f'CREATE DATABASE "{parts.database_name}"')
        return True
    finally:
        await conn.close()


async def main() -> int:
    created = await ensure_database_exists(settings.DATABASE_URL)
    if created:
        print("DB bootstrap: created database")
    else:
        print("DB bootstrap: database already exists")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
