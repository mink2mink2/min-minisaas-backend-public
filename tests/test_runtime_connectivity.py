"""실행 환경 연결성 스모크 테스트.

목적:
- 백엔드 앱 기동 가능 여부
- Redis 실제 연결 가능 여부
- PostgreSQL 실제 연결 가능 여부
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.core.cache import cache
from app.core.database import AsyncSessionLocal


@pytest.mark.integration
def test_health_endpoint_runtime_up() -> None:
    """FastAPI 앱이 실제로 응답하는지 확인."""
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json().get("status") == "ok"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_runtime_roundtrip() -> None:
    """Redis set/get/delete round-trip 확인."""
    await cache.init()

    key = f"smoke:test:{uuid.uuid4().hex}"
    payload = {"ok": True, "source": "pytest"}

    await cache.set(key, payload, ttl_seconds=30)
    loaded = await cache.get(key)
    await cache.delete(key)

    assert loaded == payload


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_runtime_select_one() -> None:
    """PostgreSQL 기본 쿼리 수행 확인."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
        value = result.scalar_one()

    assert value == 1
