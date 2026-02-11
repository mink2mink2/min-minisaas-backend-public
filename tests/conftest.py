"""테스트 설정"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.core.cache import cache


@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 설정"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_cache(monkeypatch):
    """Mock 캐시"""
    cache_data = {}

    async def mock_get(key):
        return cache_data.get(key)

    async def mock_set(key, value, ttl_seconds=None):
        cache_data[key] = value

    async def mock_delete(key):
        cache_data.pop(key, None)

    async def mock_invalidate_pattern(pattern):
        keys_to_delete = [k for k in cache_data.keys() if pattern in k]
        for k in keys_to_delete:
            del cache_data[k]

    async def mock_redis_keys(pattern):
        """Mock redis.keys() for session_manager.destroy_user_sessions()"""
        # pattern에서 * 를 제거하고 prefix 매칭
        prefix = pattern.rstrip("*")
        return [k for k in cache_data.keys() if k.startswith(prefix)]

    async def mock_incr(key):
        """Mock cache.incr() for device rate limiting"""
        if key not in cache_data:
            cache_data[key] = 0
        cache_data[key] += 1
        return cache_data[key]

    # Mock cache methods
    monkeypatch.setattr(cache, "get", mock_get)
    monkeypatch.setattr(cache, "set", mock_set)
    monkeypatch.setattr(cache, "delete", mock_delete)
    monkeypatch.setattr(cache, "invalidate_pattern", mock_invalidate_pattern)
    # For incr, we'll use a different approach since the object doesn't have incr
    cache.incr = mock_incr

    # Mock cache.redis.keys()
    mock_redis = MagicMock()
    mock_redis.keys = mock_redis_keys
    monkeypatch.setattr(cache, "redis", mock_redis)

    return cache_data


@pytest.fixture(autouse=True)
def mock_dependencies(monkeypatch):
    """Override FastAPI dependencies for testing"""
    from app.main import app
    from app.api.v1.dependencies.api_key import verify_api_key
    from app.core.database import get_db
    from app.domain.auth.services.auth_service import AuthService

    # Mock API Key - always valid
    async def mock_verify_api_key(x_api_key: str = None):
        return x_api_key or "test_key"

    # Mock database session
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock())
    mock_session.execute.return_value.scalars = MagicMock(return_value=MagicMock())
    mock_session.execute.return_value.scalars.return_value.first = MagicMock(return_value=None)
    mock_session.execute.return_value.scalars.return_value.one_or_none = MagicMock(return_value=None)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()

    async def mock_get_db():
        yield mock_session

    # Mock AuthService methods to prevent database access
    async def mock_login(self, email, password, client_type=None, user_agent=None, ip=None):
        return None  # Return None to indicate login failure

    async def mock_register(self, email, password):
        raise Exception("User already exists")

    async def mock_refresh_token(self, refresh_token, user_agent=None, ip=None):
        return None  # Return None to indicate refresh failure

    monkeypatch.setattr(AuthService, "login", mock_login)
    monkeypatch.setattr(AuthService, "register", mock_register)
    monkeypatch.setattr(AuthService, "refresh_token", mock_refresh_token)

    # Override dependencies
    app.dependency_overrides[verify_api_key] = mock_verify_api_key
    app.dependency_overrides[get_db] = mock_get_db

    yield

    # Clean up
    app.dependency_overrides.clear()
