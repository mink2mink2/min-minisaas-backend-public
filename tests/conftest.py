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
    from uuid import uuid4
    from datetime import datetime
    from app.main import app
    from app.api.v1.dependencies.api_key import verify_api_key
    from app.core.database import get_db
    from app.domain.auth.services.auth_service import AuthService

    # Mock API Key - always valid
    async def mock_verify_api_key(x_api_key: str = None):
        return x_api_key or "test_key"

    # Mock database session with proper async support
    from uuid import uuid4
    from datetime import datetime
    mock_session = MagicMock()

    # Mock FcmToken for registration
    mock_fcm_token = MagicMock()
    mock_fcm_token.id = uuid4()
    mock_fcm_token.token = "test_token"
    mock_fcm_token.platform = "android"
    mock_fcm_token.device_name = "Test Device"
    mock_fcm_token.is_active = True
    mock_fcm_token.created_at = datetime.utcnow()

    # Mock execute for queries
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_result.scalar = MagicMock(return_value=0)
    mock_result.rowcount = 0
    mock_result.all = MagicMock(return_value=[])

    mock_scalars = MagicMock()
    mock_scalars.first = MagicMock(return_value=None)
    mock_scalars.one_or_none = MagicMock(return_value=None)
    mock_scalars.all = MagicMock(return_value=[])
    mock_result.scalars = MagicMock(return_value=mock_scalars)

    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.add_all = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.delete = MagicMock()
    mock_session.flush = AsyncMock()

    async def mock_refresh(obj):
        """Mock refresh that populates created_at if missing"""
        if hasattr(obj, 'created_at') and obj.created_at is None:
            obj.created_at = datetime.utcnow()

    mock_session.refresh = AsyncMock(side_effect=mock_refresh)

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


@pytest.fixture
def client(mock_cache, mock_dependencies, monkeypatch):
    """Test client for API endpoint testing"""
    from uuid import uuid4
    from datetime import datetime
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.v1.dependencies.auth import verify_any_platform, AuthResult
    from app.domain.push.services.push_service import PushService

    # Mock auth to return valid user
    def mock_verify_any_platform():
        return AuthResult(user_id="123e4567-e89b-12d3-a456-426614174000", platform="web")

    app.dependency_overrides[verify_any_platform] = mock_verify_any_platform

    # Mock PushService methods for endpoint testing (only for this client)
    async def mock_register_token(self, user_id, token, platform, device_name=None):
        """Mock register token - returns a mock FcmToken with provided values"""
        mock_token = MagicMock()
        mock_token.id = str(uuid4())
        mock_token.token = token
        mock_token.platform = platform
        mock_token.device_name = device_name
        mock_token.is_active = True
        mock_token.created_at = datetime.utcnow()
        return mock_token

    async def mock_update_token(self, user_id, token_id, platform=None, device_name=None):
        """Mock update token"""
        mock_token = MagicMock()
        mock_token.id = token_id
        mock_token.token = f"updated_token_{token_id}"
        mock_token.platform = platform or "android"
        mock_token.device_name = device_name
        mock_token.is_active = True
        mock_token.created_at = datetime.utcnow()
        return mock_token

    async def mock_remove_token(self, user_id, token):
        """Mock remove token - returns False for non-existent tokens"""
        if "non_existent" in token or "invalid" in token:
            return False
        return True

    async def mock_mark_as_read(self, user_id, notification_id):
        """Mock mark as read"""
        return True

    async def mock_delete_notification(self, user_id, notification_id):
        """Mock delete notification"""
        return True

    async def mock_get_notifications(self, user_id, page=1, limit=20):
        """Mock get notifications"""
        mock_notif = MagicMock()
        mock_notif.id = str(uuid4())
        mock_notif.user_id = str(user_id)
        mock_notif.title = "Test Notification"
        mock_notif.body = "Test body"
        mock_notif.event_type = "test.event"
        mock_notif.related_id = None
        mock_notif.is_read = False
        mock_notif.created_at = datetime.utcnow()
        return ([mock_notif], 1)

    async def mock_get_unread_count(self, user_id):
        """Mock get unread count"""
        return 1

    monkeypatch.setattr(PushService, "register_token", mock_register_token)
    monkeypatch.setattr(PushService, "update_token", mock_update_token)
    monkeypatch.setattr(PushService, "remove_token", mock_remove_token)
    monkeypatch.setattr(PushService, "mark_as_read", mock_mark_as_read)
    monkeypatch.setattr(PushService, "delete_notification", mock_delete_notification)
    monkeypatch.setattr(PushService, "get_notifications", mock_get_notifications)
    monkeypatch.setattr(PushService, "get_unread_count", mock_get_unread_count)

    return TestClient(app)


@pytest.fixture
def client_no_auth(monkeypatch):
    """Test client WITHOUT auth mocking for testing auth-required endpoints"""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.v1.dependencies.api_key import verify_api_key
    from app.api.v1.dependencies.auth import verify_any_platform

    # Remove auth overrides so they fail
    app.dependency_overrides.clear()

    # Mock just the database to avoid import errors, but let auth fail
    from app.core.database import get_db
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock())

    async def mock_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = mock_get_db

    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Authentication headers for API requests"""
    return {
        "Authorization": "Bearer test_token",
        "X-API-Key": "test_key"
    }
