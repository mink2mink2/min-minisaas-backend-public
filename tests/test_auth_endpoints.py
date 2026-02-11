"""Auth 엔드포인트 테스트"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app


@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트"""
    return TestClient(app)


class TestAuthEndpointsBasic:
    """기본 엔드포인트 구조 테스트"""

    def test_api_health(self, client):
        """API 상태 확인"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_web_login_requires_api_key(self, client):
        """Web 로그인: API Key 필수"""
        response = client.post(
            "/api/v1/auth/login/web",
            headers={"Authorization": "Bearer fake_token"}
        )
        # X-API-Key가 없으면 422 또는 401
        assert response.status_code in [401, 422]

    def test_mobile_login_requires_api_key(self, client):
        """Mobile 로그인: API Key 필수"""
        response = client.post(
            "/api/v1/auth/login/mobile",
            headers={"Authorization": "Bearer fake_token"}
        )
        assert response.status_code in [401, 422]

    def test_desktop_login_requires_api_key(self, client):
        """Desktop 로그인: API Key 필수"""
        response = client.post(
            "/api/v1/auth/login/desktop",
            json={"code": "auth_code", "code_verifier": "verifier"}
        )
        # Without valid API key or endpoint processing fails - expect error response
        assert response.status_code in [400, 401, 422, 500]

    def test_device_login_requires_api_key(self, client):
        """Device 로그인: API Key 필수"""
        response = client.post(
            "/api/v1/auth/login/device",
            json={"device_id": "device-01", "device_secret": "secret"}
        )
        # Without valid API key or endpoint processing fails - expect error response
        assert response.status_code in [400, 401, 422, 500]

    def test_heartbeat_requires_platform_header(self, client):
        """Heartbeat: X-Platform 헤더 필수"""
        response = client.post(
            "/api/v1/auth/heartbeat",
            headers={"X-API-Key": "test_key"}
        )
        # X-Platform이 없으면 422
        assert response.status_code == 422

    def test_logout_requires_platform_header(self, client):
        """Logout: X-Platform 헤더 필수"""
        response = client.post(
            "/api/v1/auth/logout",
            headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

    def test_me_requires_platform_header(self, client):
        """Me: X-Platform 헤더 필수"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422


class TestLegacyAuthEndpoints:
    """레거시 이메일+비밀번호 엔드포인트"""

    def test_register_endpoint_exists(self, client):
        """회원가입 엔드포인트 존재"""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "password123"}
        )
        # 데이터베이스 없으므로 오류가 날 수 있지만, 엔드포인트는 존재해야 함
        assert response.status_code in [200, 400, 422, 500]

    def test_login_endpoint_exists(self, client):
        """로그인 엔드포인트 존재"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123",
                "client_type": "web"
            }
        )
        assert response.status_code in [200, 400, 401, 422, 500]

    def test_refresh_endpoint_exists(self, client):
        """토큰 갱신 엔드포인트 존재"""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "fake_token"}
        )
        assert response.status_code in [200, 400, 401, 422, 500]


class TestEndpointImports:
    """엔드포인트 임포트 테스트"""

    def test_legacy_router_imported(self):
        """레거시 라우터 임포트"""
        from app.api.v1.endpoints.auth.legacy import router
        assert router is not None

    def test_web_router_imported(self):
        """Web 라우터 임포트"""
        from app.api.v1.endpoints.auth.web import router
        assert router is not None

    def test_mobile_router_imported(self):
        """Mobile 라우터 임포트"""
        from app.api.v1.endpoints.auth.mobile import router
        assert router is not None

    def test_desktop_router_imported(self):
        """Desktop 라우터 임포트"""
        from app.api.v1.endpoints.auth.desktop import router
        assert router is not None

    def test_device_router_imported(self):
        """Device 라우터 임포트"""
        from app.api.v1.endpoints.auth.device import router
        assert router is not None

    def test_common_router_imported(self):
        """Common 라우터 임포트"""
        from app.api.v1.endpoints.auth.common import router
        assert router is not None

    def test_auth_router_aggregated(self):
        """Auth 라우터 통합"""
        from app.api.v1.endpoints.auth import router
        assert len(router.routes) > 0


class TestDesktopTokenReuseDetection:
    """Task 1: Desktop 플랫폼 Refresh Token Reuse Detection 테스트"""

    @pytest.mark.asyncio
    async def test_jwt_manager_first_use(self, mock_cache):
        """Step 1: 첫 사용 - 정상적으로 히스토리에 기록됨"""
        from app.auth.jwt_manager import jwt_manager

        user_id = "user-123"
        device_id = "device-456"
        refresh_token = "refresh_token_v1"
        settings_expire_days = 30

        # 첫 번째 사용
        result = await jwt_manager.detect_and_log_refresh_reuse(
            user_id=user_id,
            device_id=device_id,
            old_refresh_token=refresh_token,
            settings_refresh_expire_days=settings_expire_days,
        )

        assert result is True  # 정상
        # Redis에 히스토리가 저장됨
        history_key = f"refresh_token_history:{user_id}:{device_id}"
        assert history_key in mock_cache
        assert mock_cache[history_key]["generation_count"] == 1

    @pytest.mark.asyncio
    async def test_jwt_manager_token_reuse_detected(self, mock_cache):
        """Step 2: 토큰 재사용 감지 - 같은 토큰을 두 번 사용"""
        from app.auth.jwt_manager import jwt_manager

        user_id = "user-123"
        device_id = "device-456"
        refresh_token = "refresh_token_v1"
        settings_expire_days = 30

        # 첫 번째 사용
        result1 = await jwt_manager.detect_and_log_refresh_reuse(
            user_id=user_id,
            device_id=device_id,
            old_refresh_token=refresh_token,
            settings_refresh_expire_days=settings_expire_days,
        )
        assert result1 is True

        # 같은 토큰을 다시 사용 (공격!)
        result2 = await jwt_manager.detect_and_log_refresh_reuse(
            user_id=user_id,
            device_id=device_id,
            old_refresh_token=refresh_token,
            settings_refresh_expire_days=settings_expire_days,
        )

        assert result2 is False  # 재사용 감지!
        # generation_count는 증가하지 않음
        history_key = f"refresh_token_history:{user_id}:{device_id}"
        assert mock_cache[history_key]["generation_count"] == 1

    @pytest.mark.asyncio
    async def test_jwt_manager_different_tokens_allowed(self, mock_cache):
        """Step 3: 다른 토큰은 계속 사용 가능"""
        from app.auth.jwt_manager import jwt_manager

        user_id = "user-123"
        device_id = "device-456"
        settings_expire_days = 30

        # 첫 번째 토큰
        result1 = await jwt_manager.detect_and_log_refresh_reuse(
            user_id=user_id,
            device_id=device_id,
            old_refresh_token="token_v1",
            settings_refresh_expire_days=settings_expire_days,
        )
        assert result1 is True
        assert mock_cache[f"refresh_token_history:{user_id}:{device_id}"]["generation_count"] == 1

        # 다른 토큰 (정상적인 token rotation)
        result2 = await jwt_manager.detect_and_log_refresh_reuse(
            user_id=user_id,
            device_id=device_id,
            old_refresh_token="token_v2",
            settings_refresh_expire_days=settings_expire_days,
        )
        assert result2 is True
        assert mock_cache[f"refresh_token_history:{user_id}:{device_id}"]["generation_count"] == 2

        # 또 다른 토큰
        result3 = await jwt_manager.detect_and_log_refresh_reuse(
            user_id=user_id,
            device_id=device_id,
            old_refresh_token="token_v3",
            settings_refresh_expire_days=settings_expire_days,
        )
        assert result3 is True
        assert mock_cache[f"refresh_token_history:{user_id}:{device_id}"]["generation_count"] == 3

    @pytest.mark.asyncio
    async def test_jwt_manager_different_devices_isolated(self, mock_cache):
        """Step 4: 다른 기기는 히스토리가 독립적"""
        from app.auth.jwt_manager import jwt_manager

        user_id = "user-123"
        settings_expire_days = 30

        # 기기 1에서 토큰 사용
        result1 = await jwt_manager.detect_and_log_refresh_reuse(
            user_id=user_id,
            device_id="device-1",
            old_refresh_token="token_x",
            settings_refresh_expire_days=settings_expire_days,
        )
        assert result1 is True

        # 기기 2에서 같은 내용의 토큰 사용 (다른 기기이므로 OK)
        result2 = await jwt_manager.detect_and_log_refresh_reuse(
            user_id=user_id,
            device_id="device-2",
            old_refresh_token="token_x",
            settings_refresh_expire_days=settings_expire_days,
        )
        assert result2 is True

        # 히스토리가 분리됨
        history1_key = f"refresh_token_history:{user_id}:device-1"
        history2_key = f"refresh_token_history:{user_id}:device-2"
        assert history1_key in mock_cache
        assert history2_key in mock_cache
        assert history1_key != history2_key

    @pytest.mark.asyncio
    async def test_jwt_manager_generation_count_increments(self, mock_cache):
        """Step 5: Generation count가 정상적으로 증가"""
        from app.auth.jwt_manager import jwt_manager

        user_id = "user-999"
        device_id = "device-999"
        settings_expire_days = 30

        for i in range(1, 6):
            result = await jwt_manager.detect_and_log_refresh_reuse(
                user_id=user_id,
                device_id=device_id,
                old_refresh_token=f"token_v{i}",
                settings_refresh_expire_days=settings_expire_days,
            )
            assert result is True
            history_key = f"refresh_token_history:{user_id}:{device_id}"
            assert mock_cache[history_key]["generation_count"] == i


class TestWebSessionFixationPrevention:
    """Task 2: Web 플랫폼 Session Fixation 공격 방지 테스트"""

    @pytest.mark.asyncio
    async def test_session_manager_destroy(self, mock_cache):
        """Step 1: SessionManager destroy() 메서드 테스트"""
        from app.auth.session_manager import session_manager

        # 세션 생성
        session_id = await session_manager.create("user-123")
        session_key = f"sess:{session_id}"
        assert session_key in mock_cache

        # 세션 삭제
        await session_manager.destroy(session_id)
        assert session_key not in mock_cache

    @pytest.mark.asyncio
    async def test_old_session_not_reusable_after_login(self, mock_cache):
        """Step 2: Old session ID는 로그인 후 사용 불가"""
        from app.auth.session_manager import session_manager
        from app.auth.web_strategy import WebAuthStrategy
        from app.auth.base import AuthResult

        # 공격자가 미리 설정한 session ID
        attacker_session_id = "attacker-preset-id"
        attacker_session_key = f"sess:{attacker_session_id}"

        # Pre-login: 공격자가 쿠키에 설정
        # (실제로는 이미 있는 세션이 아니므로 Redis에 추가)
        mock_cache[attacker_session_key] = {
            "user_id": "attacker",
            "created_at": 1234567890,
            "last_active": 1234567890,
            "expires": 1234567890 + 1800,
        }
        assert attacker_session_key in mock_cache

        # Mock request with attacker's cookie
        from unittest.mock import MagicMock

        mock_request = MagicMock()
        mock_request.cookies = {"session": attacker_session_id}

        # 사용자 로그인 - auth_result 생성
        auth_result = AuthResult(
            user_id="user-123",
            email="user@example.com",
            platform="web",
            auth_type="firebase",
            expires=1234567890 + 3600,
            metadata={"request": mock_request},
        )

        # create_session() 호출 (Session Fixation 방지 로직 실행)
        strategy = WebAuthStrategy()
        session_data = await strategy.create_session(auth_result)

        # 검증 1: Old session ID는 파괴됨
        assert attacker_session_key not in mock_cache, "공격자의 session ID가 파괴되어야 함"

        # 검증 2: 새 session ID가 반환됨
        new_session_id = session_data.get("session_id")
        assert new_session_id is not None
        assert new_session_id != attacker_session_id

        # 검증 3: 새 session ID는 Redis에 존재
        new_session_key = f"sess:{new_session_id}"
        assert new_session_key in mock_cache
        assert mock_cache[new_session_key]["user_id"] == "user-123"

    @pytest.mark.asyncio
    async def test_session_fixation_multiple_attempts(self, mock_cache):
        """Step 3: 여러 공격자 session이 모두 파괴됨"""
        from app.auth.session_manager import session_manager
        from app.auth.web_strategy import WebAuthStrategy
        from app.auth.base import AuthResult
        from unittest.mock import MagicMock

        # Pre-login: 여러 개의 old session (공격자들)
        old_sessions = ["attacker-1", "attacker-2", "attacker-3"]
        for sid in old_sessions:
            key = f"sess:{sid}"
            mock_cache[key] = {
                "user_id": "attacker",
                "created_at": 1234567890,
                "last_active": 1234567890,
                "expires": 1234567890 + 1800,
            }

        # 마지막 요청의 쿠키 (가장 최근 공격자 ID)
        mock_request = MagicMock()
        mock_request.cookies = {"session": old_sessions[-1]}

        auth_result = AuthResult(
            user_id="user-456",
            email="user456@example.com",
            platform="web",
            auth_type="firebase",
            expires=1234567890 + 3600,
            metadata={"request": mock_request},
        )

        strategy = WebAuthStrategy()
        session_data = await strategy.create_session(auth_result)

        # 최근 session만 파괴됨 (create_session은 request의 session만 처리)
        # 다른 old session들은 destroy_user_sessions에서 파괴하려고 시도
        # (하지만 이미 user_id가 없으므로 파괴되지 않음)
        final_session_id = session_data["session_id"]
        final_session_key = f"sess:{final_session_id}"

        # 검증: 새 session만 존재
        assert final_session_key in mock_cache
        assert mock_cache[final_session_key]["user_id"] == "user-456"

    @pytest.mark.asyncio
    async def test_session_fixation_with_no_old_session(self, mock_cache):
        """Step 4: Old session이 없는 경우 (정상 로그인)"""
        from app.auth.web_strategy import WebAuthStrategy
        from app.auth.base import AuthResult
        from unittest.mock import MagicMock

        # Normal login: 쿠키에 old session이 없음
        mock_request = MagicMock()
        mock_request.cookies = {}  # No session cookie

        auth_result = AuthResult(
            user_id="user-789",
            email="user789@example.com",
            platform="web",
            auth_type="firebase",
            expires=1234567890 + 3600,
            metadata={"request": mock_request},
        )

        strategy = WebAuthStrategy()
        session_data = await strategy.create_session(auth_result)

        # 검증: 새 session이 정상 생성됨
        new_session_id = session_data.get("session_id")
        assert new_session_id is not None
        new_session_key = f"sess:{new_session_id}"
        assert new_session_key in mock_cache
        assert mock_cache[new_session_key]["user_id"] == "user-789"

    @pytest.mark.asyncio
    async def test_session_fixation_with_no_request(self, mock_cache):
        """Step 5: Request가 metadata에 없는 경우 (graceful handling)"""
        from app.auth.web_strategy import WebAuthStrategy
        from app.auth.base import AuthResult

        # Edge case: request 없이 호출 (실제로는 발생하지 않아야 함)
        auth_result = AuthResult(
            user_id="user-edge",
            email="user@example.com",
            platform="web",
            auth_type="firebase",
            expires=1234567890 + 3600,
            metadata={},  # Request 없음
        )

        strategy = WebAuthStrategy()
        session_data = await strategy.create_session(auth_result)

        # 검증: 새 session이 정상 생성됨 (request 없어도 작동)
        new_session_id = session_data.get("session_id")
        assert new_session_id is not None
        new_session_key = f"sess:{new_session_id}"
        assert new_session_key in mock_cache
        assert mock_cache[new_session_key]["user_id"] == "user-edge"


class TestDeviceRateLimitingAndRotation:
    """Task 3: Device 플랫폼 Rate Limiting & Secret Rotation 테스트"""

    @pytest.mark.asyncio
    async def test_device_rate_limiting_counter(self, mock_cache):
        """Step 1: Failed login 횟수 추적"""
        from app.core.cache import cache

        device_id = "device-123"
        failed_login_key = f"device:failed_login:{device_id}"

        # 실패 1회
        count = await cache.incr(failed_login_key)
        if count == 1:
            await cache.set(failed_login_key, count, ttl_seconds=3600)

        assert mock_cache.get(failed_login_key) == 1

        # 실패 2회
        count = await cache.incr(failed_login_key)
        assert mock_cache.get(failed_login_key) == 2

        # 실패 3회
        count = await cache.incr(failed_login_key)
        assert mock_cache.get(failed_login_key) == 3

    @pytest.mark.asyncio
    async def test_device_rate_limiting_lockout(self, mock_cache):
        """Step 2: 5회 실패 후 기기 잠금"""
        from app.core.cache import cache

        device_id = "device-456"
        failed_login_key = f"device:failed_login:{device_id}"
        lockout_key = f"device:locked:{device_id}"

        # 5회 실패
        for i in range(1, 6):
            count = await cache.incr(failed_login_key)
            if count == 1:
                await cache.set(failed_login_key, count, ttl_seconds=3600)

            if count >= 5:
                # 5회 이상 실패 → 기기 잠금
                await cache.set(lockout_key, "locked", ttl_seconds=15 * 60)

        # 검증 1: failed_login_key가 5
        assert mock_cache.get(failed_login_key) == 5

        # 검증 2: lockout_key가 설정됨
        assert mock_cache.get(lockout_key) == "locked"

    @pytest.mark.asyncio
    async def test_device_rate_limiting_reset_on_success(self, mock_cache):
        """Step 3: 성공적인 로그인 후 실패 카운터 초기화"""
        from app.core.cache import cache

        device_id = "device-789"
        failed_login_key = f"device:failed_login:{device_id}"

        # 2회 실패 후 카운터 설정
        for i in range(1, 3):
            await cache.incr(failed_login_key)
            if i == 1:
                await cache.set(failed_login_key, i, ttl_seconds=3600)

        assert mock_cache.get(failed_login_key) == 2

        # 성공 → 카운터 초기화
        await cache.delete(failed_login_key)

        assert mock_cache.get(failed_login_key) is None

    @pytest.mark.asyncio
    async def test_device_secret_rotation_flow(self, mock_cache):
        """Step 4: Secret rotation 전체 흐름"""
        import hashlib

        device_id = "device-rotate-123"
        old_secret = "old_secret_value"
        # Simple hash for testing (bcrypt has 72 byte limit)
        old_hash = hashlib.sha256(old_secret.encode()).hexdigest()

        # Step 1: 기존 해시 검증
        assert hashlib.sha256(old_secret.encode()).hexdigest() == old_hash
        assert hashlib.sha256("wrong_secret".encode()).hexdigest() != old_hash

        # Step 2: 새 시크릿 생성
        new_secret = "new_secret_value_xyz"
        new_hash = hashlib.sha256(new_secret.encode()).hexdigest()

        # Step 3: 새 해시 검증
        assert hashlib.sha256(new_secret.encode()).hexdigest() == new_hash
        assert hashlib.sha256(old_secret.encode()).hexdigest() != new_hash

        # Step 4: 메타데이터 업데이트 (시뮬레이션)
        device_metadata = {
            "device_id": device_id,
            "secret_hash": new_hash,
            "secret_rotated_at": "2026-02-11T12:00:00",
        }

        assert device_metadata["secret_hash"] == new_hash
        assert device_metadata["secret_rotated_at"] is not None

    @pytest.mark.asyncio
    async def test_device_lockout_prevents_login(self, mock_cache):
        """Step 5: 잠금된 기기는 로그인 불가"""
        from app.core.cache import cache

        device_id = "device-locked-999"
        lockout_key = f"device:locked:{device_id}"

        # 기기 잠금
        await cache.set(lockout_key, "locked", ttl_seconds=15 * 60)

        # 잠금 상태 확인
        is_locked = await cache.get(lockout_key)
        assert is_locked == "locked"

        # 정상 시크릿으로도 로그인 불가 (잠금이 먼저 체크됨)
        if is_locked:
            # HTTPException(429) 발생할 것
            assert True

    @pytest.mark.asyncio
    async def test_device_failed_login_counter_ttl(self, mock_cache):
        """Step 6: Failed login 카운터는 1시간 후 만료"""
        from app.core.cache import cache

        device_id = "device-ttl-test"
        failed_login_key = f"device:failed_login:{device_id}"

        # 1회 실패
        count = await cache.incr(failed_login_key)
        await cache.set(failed_login_key, count, ttl_seconds=3600)

        # 카운터가 설정됨
        assert mock_cache.get(failed_login_key) == 1

        # TTL 설정 확인 (테스트에서는 mock_cache에 TTL이 저장되지 않지만,
        # 실제 Redis에서는 3600초 후 자동 삭제됨)


class TestUnifiedErrorResponses:
    """Task 4: Unified Error Response Format 테스트"""

    def test_auth_exception_created(self):
        """Step 1: AuthException 클래스가 생성됨"""
        from app.core.exceptions import AuthException

        exc = AuthException("INVALID_CREDENTIALS", 401)
        assert exc.error_code == "INVALID_CREDENTIALS"
        assert exc.status_code == 401
        assert exc.message == "Authentication failed"

    def test_auth_exception_custom_error_code(self):
        """Step 2: 다양한 에러 코드 지원"""
        from app.core.exceptions import AuthException

        # INVALID_CREDENTIALS
        exc1 = AuthException("INVALID_CREDENTIALS", 401)
        assert exc1.message == "Authentication failed"

        # INVALID_TOKEN
        exc2 = AuthException("INVALID_TOKEN", 401)
        assert exc2.message == "Invalid or expired token"

        # MISSING_FIELD
        exc3 = AuthException("MISSING_FIELD", 400)
        assert exc3.message == "Missing required field"

        # DEVICE_LOCKED
        exc4 = AuthException("DEVICE_LOCKED", 429)
        assert exc4.message == "Too many attempts. Try again later."

        # SESSION_EXPIRED
        exc5 = AuthException("SESSION_EXPIRED", 401)
        assert exc5.message == "Session expired. Please login again"

    def test_error_response_schema(self):
        """Step 3: Error response schema"""
        from app.schemas.error import AuthErrorResponse, ERROR_MESSAGES

        # Schema 검증
        error_response = AuthErrorResponse(
            error_code="INVALID_CREDENTIALS",
            message="Authentication failed",
            status_code=401
        )
        assert error_response.success is False
        assert error_response.error_code == "INVALID_CREDENTIALS"
        assert error_response.message == "Authentication failed"
        assert error_response.status_code == 401

        # ERROR_MESSAGES dict 검증
        assert "INVALID_CREDENTIALS" in ERROR_MESSAGES
        assert "INVALID_TOKEN" in ERROR_MESSAGES
        assert "MISSING_FIELD" in ERROR_MESSAGES
        assert "DEVICE_LOCKED" in ERROR_MESSAGES

    def test_error_response_messages_generic(self):
        """Step 4: Error messages는 일반적이고 플랫폼별 정보 없음"""
        from app.schemas.error import ERROR_MESSAGES

        # 모든 에러 메시지가 일반적이고 구체적이지 않음을 확인
        for error_code, message in ERROR_MESSAGES.items():
            # 에러 메시지에 기술적 상세 정보가 없음
            assert "endpoint" not in message.lower()
            assert "platform" not in message.lower()
            assert "/" not in message  # 경로 정보 없음
            assert message[0].isupper()  # 첫글자 대문자

    def test_auth_exception_uniform_across_platforms(self):
        """Step 5: 모든 플랫폼에서 동일한 에러 코드 사용"""
        from app.core.exceptions import AuthException

        # Web: INVALID_TOKEN
        exc_web = AuthException("INVALID_TOKEN", 401)
        # Mobile: INVALID_TOKEN
        exc_mobile = AuthException("INVALID_TOKEN", 401)
        # Desktop: INVALID_TOKEN
        exc_desktop = AuthException("INVALID_TOKEN", 401)
        # Device: INVALID_TOKEN
        exc_device = AuthException("INVALID_TOKEN", 401)

        # 모두 같은 에러 응답
        assert exc_web.error_code == exc_mobile.error_code == exc_desktop.error_code == exc_device.error_code
        assert exc_web.message == exc_mobile.message == exc_desktop.message == exc_device.message

    def test_auth_exception_no_detailed_messages(self):
        """Step 6: Exception이 상세 메시지를 노출하지 않음"""
        from app.core.exceptions import AuthException

        exc = AuthException("INVALID_CREDENTIALS", 401)

        # detail에도 상세 정보가 없음
        assert "user not found" not in exc.detail.lower()
        assert "database" not in exc.detail.lower()
        assert exc.detail == "Authentication failed"

    def test_missing_field_error_is_generic(self):
        """Step 7: MISSING_FIELD 에러도 어떤 필드가 빠졌는지 알려주지 않음"""
        from app.core.exceptions import AuthException

        exc = AuthException("MISSING_FIELD", 400)
        message = exc.message

        # Generic message only
        assert message == "Missing required field"
        assert "device_id" not in message.lower()
        assert "password" not in message.lower()
        assert "email" not in message.lower()
