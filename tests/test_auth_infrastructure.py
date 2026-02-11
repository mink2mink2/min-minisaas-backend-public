"""Auth 인프라 기본 테스트"""
import pytest
from app.core.auth import get_strategy, WebAuthStrategy, MobileAuthStrategy, DesktopAuthStrategy, DeviceAuthStrategy, jwt_manager, session_manager, AuthResult
from app.core.auth.firebase_verifier import firebase_verifier


class TestAuthStrategyFactory:
    """Strategy 팩토리 테스트"""

    def test_get_web_strategy(self):
        """Web 전략 조회"""
        strategy = get_strategy("web")
        assert isinstance(strategy, WebAuthStrategy)

    def test_get_mobile_strategy(self):
        """Mobile 전략 조회"""
        strategy = get_strategy("mobile")
        assert isinstance(strategy, MobileAuthStrategy)

    def test_get_desktop_strategy(self):
        """Desktop 전략 조회"""
        strategy = get_strategy("desktop")
        assert isinstance(strategy, DesktopAuthStrategy)

    def test_get_device_strategy(self):
        """Device 전략 조회"""
        strategy = get_strategy("device")
        assert isinstance(strategy, DeviceAuthStrategy)

    def test_invalid_platform(self):
        """지원하지 않는 플랫폼"""
        with pytest.raises(ValueError):
            get_strategy("invalid")


class TestAuthResult:
    """AuthResult 데이터클래스 테스트"""

    def test_auth_result_creation(self):
        """AuthResult 생성"""
        result = AuthResult(
            user_id="user123",
            email="test@example.com",
            name="Test User",
            platform="web",
            auth_type="firebase",
            expires=1234567890
        )

        assert result.user_id == "user123"
        assert result.email == "test@example.com"
        assert result.name == "Test User"
        assert result.platform == "web"
        assert result.auth_type == "firebase"
        assert result.expires == 1234567890

    def test_auth_result_with_metadata(self):
        """메타데이터 포함 AuthResult"""
        result = AuthResult(
            user_id="device123",
            platform="device",
            auth_type="api_key",
            expires=9999999999,
            metadata={"device_id": "sensor-01"}
        )

        assert result.metadata["device_id"] == "sensor-01"


class TestJWTManager:
    """JWT 관리자 테스트"""

    @pytest.mark.asyncio
    async def test_jwt_manager_check_new_jwt(self, mock_cache):
        """새로운 JWT 검증"""
        is_new = await jwt_manager.check_and_mark_used(
            user_id="user123",
            iat=1000,
            exp=2000
        )
        assert is_new is True

    @pytest.mark.asyncio
    async def test_jwt_manager_detect_reuse(self, mock_cache):
        """JWT 재사용 탐지"""
        user_id = "user_reuse_test"
        iat = 3000
        exp = 4000

        # 첫 번째 사용
        first = await jwt_manager.check_and_mark_used(user_id, iat, exp)
        assert first is True

        # 두 번째 사용 (재사용)
        second = await jwt_manager.check_and_mark_used(user_id, iat, exp)
        assert second is False


class TestSessionManager:
    """세션 관리자 테스트"""

    @pytest.mark.asyncio
    async def test_session_create(self, mock_cache):
        """세션 생성"""
        session_id = await session_manager.create("user123")
        assert session_id is not None
        assert isinstance(session_id, str)
        assert len(session_id) > 0

    @pytest.mark.asyncio
    async def test_session_validate(self, mock_cache):
        """세션 검증"""
        user_id = "test_user"
        session_id = await session_manager.create(user_id)

        session_data = await session_manager.validate(session_id)
        assert session_data is not None
        assert session_data["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_session_not_found(self, mock_cache):
        """존재하지 않는 세션"""
        session_data = await session_manager.validate("nonexistent_session")
        assert session_data is None

    @pytest.mark.asyncio
    async def test_session_destroy(self, mock_cache):
        """세션 삭제"""
        session_id = await session_manager.create("user123")
        await session_manager.destroy(session_id)

        session_data = await session_manager.validate(session_id)
        assert session_data is None


class TestFirebaseVerifier:
    """Firebase 검증기 테스트"""

    def test_firebase_verifier_initialization(self):
        """Firebase 검증기 초기화"""
        assert firebase_verifier.jwks_url is not None
        assert firebase_verifier.project_id is not None

    def test_firebase_verifier_has_cache(self):
        """캐시 구조"""
        assert isinstance(firebase_verifier.public_keys, dict)
        assert isinstance(firebase_verifier.keys_updated_at, (int, float))
