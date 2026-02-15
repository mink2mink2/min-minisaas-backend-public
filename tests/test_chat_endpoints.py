"""Chat 엔드포인트 기본 테스트"""
from fastapi.testclient import TestClient

from app.main import app


def test_chat_routes_registered():
    """OpenAPI에 chat 라우트가 노출되어야 한다."""
    client = TestClient(app)
    openapi = client.get("/openapi.json").json()
    assert "/api/v1/chat/rooms" in openapi["paths"]
    assert "/api/v1/chat/rooms/{room_id}/messages" in openapi["paths"]


def test_chat_rooms_requires_headers():
    """채팅방 목록은 인증 헤더가 없으면 실패해야 한다."""
    client = TestClient(app)
    response = client.get("/api/v1/chat/rooms")
    assert response.status_code == 422


def test_chat_create_room_requires_headers():
    """채팅방 생성은 인증 헤더가 없으면 실패해야 한다."""
    client = TestClient(app)
    response = client.post("/api/v1/chat/rooms", json={"name": "room-1"})
    assert response.status_code == 422
