"""Runtime connectivity verification for backend dependencies.

Usage:
  .venv/bin/python scripts/verify_runtime.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path

import asyncpg
import redis.asyncio as redis

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings


def normalized_pg_url(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://")


async def verify_postgres() -> None:
    conn = await asyncpg.connect(normalized_pg_url(settings.DATABASE_URL))
    try:
        value = await conn.fetchval("SELECT 1")
        if value != 1:
            raise RuntimeError(f"Unexpected SELECT 1 result: {value}")
    finally:
        await conn.close()


async def verify_redis() -> None:
    client = redis.from_url(settings.REDIS_URL_WITH_AUTH)
    key = f"verify:redis:{uuid.uuid4().hex}"
    payload = {"ok": True}

    try:
        await client.setex(key, 10, json.dumps(payload))
        loaded = await client.get(key)
        await client.delete(key)
        if not loaded:
            raise RuntimeError("Redis round-trip failed")
    finally:
        await client.aclose()


async def main() -> int:
    await verify_postgres()
    await verify_redis()
    print("VERIFY PASS: postgres + redis connectivity is healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
