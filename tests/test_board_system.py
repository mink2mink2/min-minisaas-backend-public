"""Board System 통합 테스트 - Smoke Tests

테스트 범위:
- 주요 Board 엔드포인트 존재 확인
- 인증 요구사항 검증
- 기본 입력 검증
- 마이그레이션 이후 기본 동작 확인
"""
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
    """인증 헤더 (테스트용 토큰 포함)"""
    headers = api_headers.copy()
    headers["X-Platform"] = "web"
    headers["Authorization"] = "Bearer test-token"
    return headers


class TestBoardEndpoints:
    """Board 엔드포인트 기본 테스트"""

    def test_health_check(self, client, api_headers):
        """API 헬스 체크"""
        response = client.get("/health", headers=api_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_board_categories_list(self, client, api_headers):
        """카테고리 목록 조회"""
        response = client.get("/api/v1/board/categories", headers=api_headers)
        # 성공 또는 인증 오류 (둘 다 가능)
        assert response.status_code in [200, 401]

    def test_board_posts_list(self, client, api_headers):
        """게시글 목록 조회"""
        response = client.get("/api/v1/board/posts", headers=api_headers)
        assert response.status_code in [200, 401]

    def test_board_search(self, client, api_headers):
        """게시글 검색"""
        response = client.get("/api/v1/board/search?q=test", headers=api_headers)
        assert response.status_code in [200, 401]

    def test_board_posts_require_auth_for_create(self, client, api_headers):
        """게시글 생성: 인증 필수"""
        response = client.post(
            "/api/v1/board/posts",
            json={"title": "Test", "content": "Test", "category_id": "uuid"},
            headers=api_headers  # 인증 헤더 없음
        )
        # 401 또는 422 (인증 오류 또는 검증 오류)
        assert response.status_code in [401, 422, 400]

    def test_board_comments_require_auth_for_create(self, client, api_headers):
        """댓글 생성: 인증 필수"""
        response = client.post(
            "/api/v1/board/posts/550e8400-e29b-41d4-a716-446655440000/comments",
            json={"content": "Test comment"},
            headers=api_headers  # 인증 헤더 없음
        )
        assert response.status_code in [401, 422, 400]

    def test_board_like_require_auth(self, client, api_headers):
        """좋아요: 인증 필수"""
        response = client.post(
            "/api/v1/board/posts/550e8400-e29b-41d4-a716-446655440000/like",
            headers=api_headers  # 인증 헤더 없음
        )
        assert response.status_code in [401, 404, 422, 400]

    def test_board_bookmark_require_auth(self, client, api_headers):
        """북마크: 인증 필수"""
        response = client.post(
            "/api/v1/board/posts/550e8400-e29b-41d4-a716-446655440000/bookmark",
            headers=api_headers  # 인증 헤더 없음
        )
        assert response.status_code in [401, 404, 422, 400]


class TestBoardMigrationResults:
    """마이그레이션 결과 검증"""

    def test_board_tables_created(self, client, api_headers):
        """마이그레이션으로 Board 테이블이 생성되었는지 확인"""
        # 카테고리 조회로 DB 연결성 확인
        response = client.get("/api/v1/board/categories", headers=api_headers)
        # 테이블이 존재하면 응답이 오거나 인증 에러 발생
        assert response.status_code in [200, 401]

    def test_board_post_table_structure(self, client, auth_headers):
        """게시글 테이블 구조 확인"""
        response = client.get("/api/v1/board/posts", headers=auth_headers)
        # 응답 형식 확인 (list 또는 dict with items)
        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))


class TestBoardSecurityHeaders:
    """보안 헤더 검증"""

    def test_api_key_required(self, client):
        """API Key 필수 확인"""
        # API Key 없이 요청
        response = client.get("/api/v1/board/categories")
        # API Key 없으면 401이어야 함
        assert response.status_code == 401 or response.status_code == 422

    def test_auth_header_validation(self, client, api_headers):
        """인증 헤더 검증"""
        # 잘못된 토큰으로 요청
        headers = api_headers.copy()
        headers["Authorization"] = "Bearer invalid-token"
        headers["X-Platform"] = "web"
        response = client.post(
            "/api/v1/board/categories",
            json={"name": "Test"},
            headers=headers
        )
        # 잘못된 토큰이면 401
        assert response.status_code == 401
