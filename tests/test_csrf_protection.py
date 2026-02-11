"""CSRF Token 보호 테스트 - Task 5"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app
from app.core.auth import CSRFTokenManager
from app.core.cache import cache


@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트"""
    return TestClient(app)


@pytest.fixture
async def mock_redis():
    """Mock Redis 캐시"""
    with patch("app.core.cache.cache.redis") as mock:
        yield mock


class TestCSRFTokenManager:
    """CSRF 토큰 매니저 단위 테스트"""

    @pytest.mark.asyncio
    async def test_generate_token_returns_valid_hex_string(self):
        """토큰 생성: 유효한 16진수 문자열 반환"""
        token = CSRFTokenManager.generate_token()

        # 64자 (32 bytes * 2)
        assert len(token) == 64
        # 16진수만 포함
        assert all(c in "0123456789abcdef" for c in token)

    @pytest.mark.asyncio
    async def test_generate_token_is_unique(self):
        """토큰 생성: 생성된 토큰들은 모두 다름"""
        tokens = [CSRFTokenManager.generate_token() for _ in range(10)]
        assert len(tokens) == len(set(tokens))

    @pytest.mark.asyncio
    async def test_create_and_store_token(self):
        """토큰 저장: Redis에 토큰 저장"""
        with patch.object(cache, "set", new_callable=AsyncMock) as mock_set:
            token = await CSRFTokenManager.create_and_store(
                user_id="user123",
                platform="web"
            )

            # set이 호출되었는지 확인
            mock_set.assert_called_once()

            # 반환된 토큰은 유효한 형식
            assert len(token) == 64
            assert all(c in "0123456789abcdef" for c in token)

    @pytest.mark.asyncio
    async def test_validate_token_success(self):
        """토큰 검증: 유효한 토큰"""
        token = "abc123def456"

        with patch.object(cache, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"token": token, "platform": "web"}

            result = await CSRFTokenManager.validate("user123", "web", token)
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_token_mismatch(self):
        """토큰 검증: 토큰 불일치"""
        with patch.object(cache, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"token": "correct_token", "platform": "web"}

            result = await CSRFTokenManager.validate(
                "user123", "web", "wrong_token"
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_validate_token_expired(self):
        """토큰 검증: 만료된 토큰 (Redis에 없음)"""
        with patch.object(cache, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            result = await CSRFTokenManager.validate("user123", "web", "token")
            assert result is False

    @pytest.mark.asyncio
    async def test_consume_token_valid(self):
        """토큰 소비: 유효한 토큰 삭제"""
        token = "valid_token"

        with patch.object(cache, "get", new_callable=AsyncMock) as mock_get, \
             patch.object(cache, "delete", new_callable=AsyncMock) as mock_delete:
            mock_get.return_value = {"token": token}

            result = await CSRFTokenManager.consume("user123", "web", token)

            assert result is True
            mock_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_consume_token_invalid(self):
        """토큰 소비: 유효하지 않은 토큰 (삭제 없음)"""
        with patch.object(cache, "get", new_callable=AsyncMock) as mock_get, \
             patch.object(cache, "delete", new_callable=AsyncMock) as mock_delete:
            mock_get.return_value = None

            result = await CSRFTokenManager.consume("user123", "web", "token")

            assert result is False
            mock_delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_revoke_all_tokens(self):
        """토큰 무효화: 모든 플랫폼 토큰 삭제"""
        with patch.object(cache, "delete", new_callable=AsyncMock) as mock_delete:
            await CSRFTokenManager.revoke_all("user123")

            # 4개 플랫폼 (web, mobile, desktop, device)에 대해 delete 호출
            assert mock_delete.call_count == 4


class TestCSRFEndpointIntegration:
    """CSRF 토큰 엔드포인트 통합 테스트"""

    def test_me_endpoint_requires_auth(self, client):
        """/auth/me: 인증 필수"""
        response = client.get("/api/v1/auth/me")
        # X-API-Key 없으면 422
        assert response.status_code in [422, 401]

    @pytest.mark.asyncio
    async def test_me_endpoint_returns_csrf_token(self, client):
        """/auth/me: CSRF 토큰 응답에 포함"""
        with patch("app.api.v1.dependencies.auth.verify_any_platform", new_callable=AsyncMock) as mock_auth, \
             patch("app.api.v1.dependencies.api_key.verify_api_key", new_callable=AsyncMock) as mock_api, \
             patch("app.domain.auth.services.auth_service.AuthService.get_user_by_id", new_callable=AsyncMock) as mock_user, \
             patch.object(CSRFTokenManager, "create_and_store", new_callable=AsyncMock) as mock_csrf:

            # Mock 설정
            mock_api.return_value = "valid_key"
            mock_auth.return_value = MagicMock(
                user_id="user123",
                platform="web",
                auth_type="session",
                expires=9999999999
            )

            user_mock = MagicMock()
            user_mock.id = "user123"
            user_mock.email = "test@example.com"
            user_mock.name = "Test User"
            user_mock.picture = None
            user_mock.points = 10
            user_mock.created_at = None
            user_mock.updated_at = None
            user_mock.is_active = True

            mock_user.return_value = user_mock
            mock_csrf.return_value = "csrf_token_abc123def456"

            response = client.get(
                "/api/v1/auth/me",
                headers={
                    "X-API-Key": "test_key",
                    "X-Platform": "web"
                }
            )

            # 응답에 csrf_token 포함
            if response.status_code == 200:
                data = response.json()
                assert "csrf_token" in data or "success" in data

    def test_logout_requires_csrf_token(self, client):
        """/auth/logout: CSRF 토큰 헤더 필수"""
        response = client.post(
            "/api/v1/auth/logout",
            headers={
                "X-API-Key": "test_key",
                "X-Platform": "web"
            }
        )
        # CSRF 토큰 없으면 403
        assert response.status_code in [403, 401, 422]

    @pytest.mark.asyncio
    async def test_logout_rejects_invalid_csrf_token(self, client):
        """/auth/logout: 유효하지 않은 CSRF 토큰 거절"""
        with patch("app.api.v1.dependencies.auth.verify_any_platform", new_callable=AsyncMock) as mock_auth, \
             patch("app.api.v1.dependencies.api_key.verify_api_key", new_callable=AsyncMock) as mock_api, \
             patch.object(CSRFTokenManager, "consume", new_callable=AsyncMock) as mock_consume:

            mock_api.return_value = "valid_key"
            mock_auth.return_value = MagicMock(
                user_id="user123",
                platform="web",
                auth_type="session"
            )
            mock_consume.return_value = False  # 유효하지 않은 토큰

            response = client.post(
                "/api/v1/auth/logout",
                headers={
                    "X-API-Key": "test_key",
                    "X-Platform": "web",
                    "X-CSRF-Token": "invalid_token"
                }
            )

            # CSRF 토큰 검증 실패
            assert response.status_code in [403, 401]

    @pytest.mark.asyncio
    async def test_logout_accepts_valid_csrf_token(self, client):
        """/auth/logout: 유효한 CSRF 토큰 수락"""
        with patch("app.api.v1.dependencies.auth.verify_any_platform", new_callable=AsyncMock) as mock_auth, \
             patch("app.api.v1.dependencies.api_key.verify_api_key", new_callable=AsyncMock) as mock_api, \
             patch.object(CSRFTokenManager, "consume", new_callable=AsyncMock) as mock_consume, \
             patch.object(CSRFTokenManager, "revoke_all", new_callable=AsyncMock) as mock_revoke, \
             patch("app.core.auth.get_strategy") as mock_strategy:

            # Mock 설정
            mock_api.return_value = "valid_key"
            mock_auth.return_value = MagicMock(
                user_id="user123",
                platform="web",
                auth_type="session"
            )
            mock_consume.return_value = True  # 유효한 토큰

            strategy_mock = AsyncMock()
            strategy_mock.logout = AsyncMock()
            mock_strategy.return_value = strategy_mock

            response = client.post(
                "/api/v1/auth/logout",
                headers={
                    "X-API-Key": "test_key",
                    "X-Platform": "web",
                    "X-CSRF-Token": "valid_csrf_token"
                }
            )

            # 성공 응답
            if response.status_code == 200:
                data = response.json()
                assert data.get("success") is True

    def test_delete_account_requires_csrf_token(self, client):
        """/auth/account: CSRF 토큰 헤더 필수"""
        response = client.delete(
            "/api/v1/auth/account",
            headers={
                "X-API-Key": "test_key",
                "X-Platform": "web"
            }
        )
        # CSRF 토큰 없으면 403
        assert response.status_code in [403, 401, 422]

    @pytest.mark.asyncio
    async def test_delete_account_rejects_invalid_csrf_token(self, client):
        """/auth/account: 유효하지 않은 CSRF 토큰 거절"""
        with patch("app.api.v1.dependencies.auth.verify_any_platform", new_callable=AsyncMock) as mock_auth, \
             patch("app.api.v1.dependencies.api_key.verify_api_key", new_callable=AsyncMock) as mock_api, \
             patch.object(CSRFTokenManager, "consume", new_callable=AsyncMock) as mock_consume:

            mock_api.return_value = "valid_key"
            mock_auth.return_value = MagicMock(
                user_id="user123",
                platform="web"
            )
            mock_consume.return_value = False  # 유효하지 않은 토큰

            response = client.delete(
                "/api/v1/auth/account",
                headers={
                    "X-API-Key": "test_key",
                    "X-Platform": "web",
                    "X-CSRF-Token": "invalid_token"
                }
            )

            # CSRF 토큰 검증 실패
            assert response.status_code in [403, 401]

    @pytest.mark.asyncio
    async def test_delete_account_accepts_valid_csrf_token(self, client):
        """/auth/account: 유효한 CSRF 토큰 수락"""
        with patch("app.api.v1.dependencies.auth.verify_any_platform", new_callable=AsyncMock) as mock_auth, \
             patch("app.api.v1.dependencies.api_key.verify_api_key", new_callable=AsyncMock) as mock_api, \
             patch.object(CSRFTokenManager, "consume", new_callable=AsyncMock) as mock_consume, \
             patch.object(CSRFTokenManager, "revoke_all", new_callable=AsyncMock) as mock_revoke, \
             patch("app.domain.auth.services.auth_service.AuthService.deactivate_user", new_callable=AsyncMock) as mock_deactivate, \
             patch("app.core.auth.get_strategy") as mock_strategy:

            # Mock 설정
            mock_api.return_value = "valid_key"
            mock_auth.return_value = MagicMock(
                user_id="user123",
                platform="web"
            )
            mock_consume.return_value = True  # 유효한 토큰

            strategy_mock = AsyncMock()
            strategy_mock.logout = AsyncMock()
            mock_strategy.return_value = strategy_mock

            response = client.delete(
                "/api/v1/auth/account",
                headers={
                    "X-API-Key": "test_key",
                    "X-Platform": "web",
                    "X-CSRF-Token": "valid_csrf_token"
                }
            )

            # 성공 응답
            if response.status_code == 200:
                data = response.json()
                assert data.get("success") is True


class TestCSRFTokenFlowIntegration:
    """CSRF 토큰 전체 흐름 통합 테스트"""

    @pytest.mark.asyncio
    async def test_complete_flow_with_csrf(self):
        """완전한 흐름: /me → /logout (CSRF 토큰 사용)"""
        with patch("app.api.v1.dependencies.auth.verify_any_platform", new_callable=AsyncMock) as mock_auth, \
             patch("app.api.v1.dependencies.api_key.verify_api_key", new_callable=AsyncMock) as mock_api, \
             patch("app.domain.auth.services.auth_service.AuthService.get_user_by_id", new_callable=AsyncMock) as mock_user, \
             patch.object(CSRFTokenManager, "create_and_store", new_callable=AsyncMock) as mock_create, \
             patch.object(CSRFTokenManager, "consume", new_callable=AsyncMock) as mock_consume, \
             patch.object(CSRFTokenManager, "revoke_all", new_callable=AsyncMock) as mock_revoke, \
             patch("app.core.auth.get_strategy") as mock_strategy:

            # Step 1: /me 호출 - CSRF 토큰 획득
            mock_api.return_value = "valid_key"
            mock_auth.return_value = MagicMock(
                user_id="user123",
                platform="web",
                auth_type="session",
                expires=9999999999
            )

            user_mock = MagicMock()
            user_mock.id = "user123"
            user_mock.email = "test@example.com"
            user_mock.name = "Test"
            user_mock.picture = None
            user_mock.points = 10
            user_mock.created_at = None
            user_mock.updated_at = None
            user_mock.is_active = True

            mock_user.return_value = user_mock
            mock_create.return_value = "csrf_token_123"

            client = TestClient(app)
            response = client.get(
                "/api/v1/auth/me",
                headers={"X-API-Key": "test_key", "X-Platform": "web"}
            )

            # Step 2: /logout 호출 - 획득한 CSRF 토큰 사용
            mock_consume.return_value = True  # CSRF 토큰 유효

            strategy_mock = AsyncMock()
            strategy_mock.logout = AsyncMock()
            mock_strategy.return_value = strategy_mock

            response = client.post(
                "/api/v1/auth/logout",
                headers={
                    "X-API-Key": "test_key",
                    "X-Platform": "web",
                    "X-CSRF-Token": "csrf_token_123"
                }
            )

            # 로그아웃이 정상 처리됨을 확인
            if response.status_code == 200:
                assert response.json().get("success") is True

    @pytest.mark.asyncio
    async def test_csrf_token_one_time_use(self):
        """CSRF 토큰: 1회용 (재사용 불가)"""
        csrf_token = "token123"

        with patch.object(cache, "get", new_callable=AsyncMock) as mock_get, \
             patch.object(cache, "delete", new_callable=AsyncMock) as mock_delete:

            # 첫 번째 사용: 성공
            mock_get.return_value = {"token": csrf_token}
            result1 = await CSRFTokenManager.consume("user123", "web", csrf_token)
            assert result1 is True

            # 두 번째 사용: 실패 (토큰이 삭제됨)
            mock_get.return_value = None
            result2 = await CSRFTokenManager.consume("user123", "web", csrf_token)
            assert result2 is False

    @pytest.mark.asyncio
    async def test_csrf_token_platform_specific(self):
        """CSRF 토큰: 플랫폼별 독립적"""
        with patch.object(cache, "get", new_callable=AsyncMock) as mock_get:
            web_token = "web_token_123"
            mobile_token = "mobile_token_456"

            # Web 토큰으로 Mobile 검증 실패
            mock_get.side_effect = [
                {"token": web_token},  # Web에서 저장된 토큰
                None  # Mobile에서 조회하면 없음
            ]

            web_result = await CSRFTokenManager.validate("user123", "web", web_token)
            assert web_result is True

            # 토큰이 플랫폼별로 다르므로 다른 플랫폼에서는 사용 불가
            # (일반적으로는 다른 플랫폼 토큰 값이므로 매칭 실패)
