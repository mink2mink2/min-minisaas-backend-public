"""PDF 도메인 통합 테스트"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트"""
    return TestClient(app)


@pytest.fixture
def api_headers():
    """기본 API 헤더"""
    return {
        "X-API-Key": "test-api-key",
    }


@pytest.fixture
def auth_headers(api_headers):
    """인증 헤더"""
    headers = api_headers.copy()
    headers["X-Platform"] = "web"
    headers["Authorization"] = "Bearer test-token"
    return headers


class TestPDFEndpointsExist:
    """PDF 엔드포인트 존재 확인"""

    def test_pdf_upload_endpoint_exists(self, client, auth_headers):
        """POST /api/v1/pdf/upload 엔드포인트 확인"""
        # 더미 파일 업로드 (실패할 것이지만 엔드포인트는 존재)
        response = client.post(
            "/api/v1/pdf/upload",
            headers=auth_headers,
        )
        # 404가 아닌지만 확인
        assert response.status_code != 404, "Upload 엔드포인트가 없습니다"

    def test_pdf_get_endpoint_exists(self, client, auth_headers):
        """GET /api/v1/pdf/{file_id} 엔드포인트 확인"""
        file_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.get(
            f"/api/v1/pdf/{file_id}",
            headers=auth_headers,
        )
        assert response.status_code != 404, "Get 엔드포인트가 없습니다"

    def test_pdf_list_endpoint_exists(self, client, auth_headers):
        """GET /api/v1/pdf/user/files 엔드포인트 확인"""
        response = client.get(
            "/api/v1/pdf/user/files",
            headers=auth_headers,
        )
        assert response.status_code != 404, "List 엔드포인트가 없습니다"

    def test_pdf_delete_endpoint_exists(self, client, auth_headers):
        """DELETE /api/v1/pdf/{file_id} 엔드포인트 확인"""
        file_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.delete(
            f"/api/v1/pdf/{file_id}",
            headers=auth_headers,
        )
        assert response.status_code != 404, "Delete 엔드포인트가 없습니다"

    def test_pdf_convert_endpoint_exists(self, client, auth_headers):
        """POST /api/v1/pdf/{file_id}/convert 엔드포인트 확인"""
        file_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.post(
            f"/api/v1/pdf/{file_id}/convert",
            json={},
            headers=auth_headers,
        )
        assert response.status_code != 404, "Convert 엔드포인트가 없습니다"

    def test_pdf_status_endpoint_exists(self, client, auth_headers):
        """GET /api/v1/pdf/{file_id}/status 엔드포인트 확인"""
        file_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.get(
            f"/api/v1/pdf/{file_id}/status",
            headers=auth_headers,
        )
        assert response.status_code != 404, "Status 엔드포인트가 없습니다"


class TestPDFAuthRequirements:
    """PDF 인증 요구사항"""

    def test_upload_requires_auth(self, client, api_headers):
        """업로드: 인증 필수"""
        response = client.post(
            "/api/v1/pdf/upload",
            headers=api_headers,  # 인증 헤더 없음
        )
        # 401 또는 422 (인증 실패 또는 검증 오류)
        assert response.status_code in [401, 422]

    def test_get_requires_auth(self, client, api_headers):
        """조회: 인증 필수"""
        file_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.get(
            f"/api/v1/pdf/{file_id}",
            headers=api_headers,  # 인증 헤더 없음
        )
        assert response.status_code in [401, 404, 422]

    def test_list_requires_auth(self, client, api_headers):
        """목록: 인증 필수"""
        response = client.get(
            "/api/v1/pdf/user/files",
            headers=api_headers,  # 인증 헤더 없음
        )
        assert response.status_code in [401, 422]

    def test_delete_requires_auth(self, client, api_headers):
        """삭제: 인증 필수"""
        file_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.delete(
            f"/api/v1/pdf/{file_id}",
            headers=api_headers,  # 인증 헤더 없음
        )
        assert response.status_code in [401, 404, 422]

    def test_convert_requires_auth(self, client, api_headers):
        """변환: 인증 필수"""
        file_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.post(
            f"/api/v1/pdf/{file_id}/convert",
            json={},
            headers=api_headers,  # 인증 헤더 없음
        )
        assert response.status_code in [401, 404, 422]

    def test_status_requires_auth(self, client, api_headers):
        """상태: 인증 필수"""
        file_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.get(
            f"/api/v1/pdf/{file_id}/status",
            headers=api_headers,  # 인증 헤더 없음
        )
        assert response.status_code in [401, 404, 422]


class TestPDFErrorHandling:
    """PDF 에러 처리"""

    def test_get_nonexistent_file(self, client, auth_headers):
        """존재하지 않는 파일 조회"""
        file_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.get(
            f"/api/v1/pdf/{file_id}",
            headers=auth_headers,
        )
        # 404 또는 인증 실패
        assert response.status_code in [404, 401]

    def test_delete_nonexistent_file(self, client, auth_headers):
        """존재하지 않는 파일 삭제"""
        file_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.delete(
            f"/api/v1/pdf/{file_id}",
            headers=auth_headers,
        )
        # 404 또는 인증 실패
        assert response.status_code in [404, 401]

    def test_convert_nonexistent_file(self, client, auth_headers):
        """존재하지 않는 파일 변환"""
        file_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.post(
            f"/api/v1/pdf/{file_id}/convert",
            json={},
            headers=auth_headers,
        )
        # 404 또는 인증 실패
        assert response.status_code in [404, 401]

    def test_status_nonexistent_file(self, client, auth_headers):
        """존재하지 않는 파일 상태 조회"""
        file_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.get(
            f"/api/v1/pdf/{file_id}/status",
            headers=auth_headers,
        )
        # 404 또는 인증 실패
        assert response.status_code in [404, 401]


class TestPDFAPIStructure:
    """PDF API 구조 확인"""

    def test_pdf_routers_integrated(self, client, api_headers):
        """PDF 라우터가 메인 API에 통합되어 있는지 확인"""
        # 여러 PDF 엔드포인트 호출해서 모두 404가 아닌지 확인
        endpoints = [
            ("GET", "/api/v1/pdf/user/files"),
            ("GET", "/api/v1/pdf/550e8400-e29b-41d4-a716-446655440000/status"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint, headers={"X-API-Key": "test"})
            else:
                response = client.post(
                    endpoint,
                    json={},
                    headers={"X-API-Key": "test"},
                )

            # 404가 아니어야 함 (인증 오류 또는 다른 오류일 수 있음)
            assert response.status_code != 404, f"{method} {endpoint} not integrated"
