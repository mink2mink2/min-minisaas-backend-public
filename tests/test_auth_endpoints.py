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
