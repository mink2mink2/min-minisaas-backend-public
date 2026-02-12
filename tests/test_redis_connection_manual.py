"""Manual Redis connectivity test.

Run:
    .venv/bin/python tests/test_redis_connection_manual.py
"""

import asyncio
import json
import sys
import uuid

import redis.asyncio as redis

from app.core.config import settings


async def main() -> int:
    client = redis.from_url(settings.REDIS_URL)
    key = f"manual:redis:test:{uuid.uuid4().hex}"
    payload = {"ok": True, "source": "manual-test"}

    try:
        await client.setex(key, 30, json.dumps(payload))
        raw = await client.get(key)
        await client.delete(key)
        await client.aclose()

        if not raw:
            print("FAIL: value not found after set")
            return 1

        loaded = json.loads(raw)
        if loaded != payload:
            print(f"FAIL: payload mismatch loaded={loaded}")
            return 1

        print("PASS: Redis connect + set/get/delete round-trip succeeded")
        print(f"REDIS_URL={settings.REDIS_URL}")
        return 0
    except Exception as exc:
        print(f"FAIL: Redis connectivity test failed: {exc}")
        print(f"REDIS_URL={settings.REDIS_URL}")
        return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
