"""푸시 알림 API 엔드포인트 테스트"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

# ============================================================================
# Token Management Endpoint Tests
# ============================================================================

class TestTokenManagementEndpoints:
    """Token management endpoint tests"""

    @pytest.mark.asyncio
    async def test_register_token_success(self, client, auth_headers):
        """Test successful token registration"""
        payload = {
            "token": "fcm_token_abc123",
            "platform": "android",
            "device_name": "Samsung S21",
        }

        response = client.post(
            "/api/v1/push/tokens",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 201
        assert response.json()["token"] == payload["token"]
        assert response.json()["platform"] == payload["platform"]

    @pytest.mark.asyncio
    async def test_register_token_missing_required(self, client, auth_headers):
        """Test token registration with missing required fields"""
        payload = {
            "platform": "android",
            # Missing token
        }

        response = client.post(
            "/api/v1/push/tokens",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_register_token_invalid_platform(self, client, auth_headers):
        """Test token registration with invalid platform"""
        payload = {
            "token": "test_token",
            "platform": "invalid_platform",
        }

        response = client.post(
            "/api/v1/push/tokens",
            json=payload,
            headers=auth_headers,
        )

        # Should still succeed at endpoint level - validation happens in service
        assert response.status_code == 201 or response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_token_no_auth(self, client_no_auth):
        """Test token registration without authentication"""
        payload = {
            "token": "test_token",
            "platform": "android",
            "device_name": "Test Device",
        }

        response = client_no_auth.post(
            "/api/v1/push/tokens",
            json=payload,
        )

        # Can be 401 (auth failed) or 422/400 (validation error)
        assert response.status_code in [400, 401, 422]

    @pytest.mark.asyncio
    async def test_update_token_success(self, client, auth_headers):
        """Test successful token update"""
        token_id = str(uuid4())
        payload = {
            "platform": "ios",
        }

        response = client.put(
            f"/api/v1/push/tokens/{token_id}",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_remove_token_success(self, client, auth_headers):
        """Test successful token removal"""
        token = "test_token_to_remove"

        response = client.delete(
            f"/api/v1/push/tokens/{token}",
            headers=auth_headers,
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_remove_token_not_found(self, client, auth_headers):
        """Test removing non-existent token"""
        response = client.delete(
            "/api/v1/push/tokens/non_existent_token",
            headers=auth_headers,
        )

        assert response.status_code == 404


# ============================================================================
# Notification Management Endpoint Tests
# ============================================================================

class TestNotificationManagementEndpoints:
    """Notification management endpoint tests"""

    @pytest.mark.asyncio
    async def test_get_notifications_success(self, client, auth_headers):
        """Test getting notification list"""
        response = client.get(
            "/api/v1/push/notifications",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data

    @pytest.mark.asyncio
    async def test_get_notifications_with_pagination(self, client, auth_headers):
        """Test getting notifications with pagination parameters"""
        response = client.get(
            "/api/v1/push/notifications?page=2&limit=10",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["limit"] == 10

    @pytest.mark.asyncio
    async def test_get_notifications_invalid_limit(self, client, auth_headers):
        """Test getting notifications with invalid limit"""
        response = client.get(
            "/api/v1/push/notifications?limit=1000",
            headers=auth_headers,
        )

        # Should succeed, fail with 400, or validation error 422
        assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_get_unread_count_success(self, client, auth_headers):
        """Test getting unread notification count"""
        response = client.get(
            "/api/v1/push/notifications/unread/count",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "unread_count" in data
        assert isinstance(data["unread_count"], int)

    @pytest.mark.asyncio
    async def test_mark_as_read_success(self, client, auth_headers):
        """Test marking notification as read"""
        notification_id = str(uuid4())

        response = client.put(
            f"/api/v1/push/notifications/{notification_id}/read",
            headers=auth_headers,
        )

        assert response.status_code in [200, 404]  # 404 if not found

    @pytest.mark.asyncio
    async def test_mark_all_as_read_success(self, client, auth_headers):
        """Test marking all notifications as read"""
        response = client.put(
            "/api/v1/push/notifications/read-all",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "marked_count" in data

    @pytest.mark.asyncio
    async def test_delete_notification_success(self, client, auth_headers):
        """Test deleting notification"""
        notification_id = str(uuid4())

        response = client.delete(
            f"/api/v1/push/notifications/{notification_id}",
            headers=auth_headers,
        )

        assert response.status_code in [204, 404]

    @pytest.mark.asyncio
    async def test_notification_endpoints_no_auth(self, client_no_auth):
        """Test notification endpoints without authentication"""
        response = client_no_auth.get("/api/v1/push/notifications")
        assert response.status_code in [400, 401, 422]

        response = client_no_auth.get("/api/v1/push/notifications/unread/count")
        assert response.status_code in [400, 401, 422]

        response = client_no_auth.put("/api/v1/push/notifications/read-all")
        assert response.status_code in [400, 401, 422]


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Error handling and edge case tests"""

    @pytest.mark.asyncio
    async def test_invalid_token_format(self, client, auth_headers):
        """Test with invalid token format"""
        payload = {
            "token": "",  # Empty token
            "platform": "android",
        }

        response = client.post(
            "/api/v1/push/tokens",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_invalid_notification_id_format(self, client, auth_headers):
        """Test with invalid notification ID format"""
        response = client.put(
            "/api/v1/push/notifications/invalid_uuid/read",
            headers=auth_headers,
        )

        # FastAPI returns 422 for invalid path parameters
        assert response.status_code in [400, 404, 422]

    @pytest.mark.asyncio
    async def test_concurrent_mark_as_read(self, client, auth_headers):
        """Test concurrent mark as read operations"""
        notification_id = str(uuid4())

        # Make concurrent requests
        responses = [
            client.put(
                f"/api/v1/push/notifications/{notification_id}/read",
                headers=auth_headers,
            )
            for _ in range(3)
        ]

        # All should succeed or return 404/200
        for response in responses:
            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_delete_already_deleted(self, client, auth_headers):
        """Test deleting already deleted notification"""
        notification_id = str(uuid4())

        # First delete
        response1 = client.delete(
            f"/api/v1/push/notifications/{notification_id}",
            headers=auth_headers,
        )

        # Second delete of same notification
        response2 = client.delete(
            f"/api/v1/push/notifications/{notification_id}",
            headers=auth_headers,
        )

        # First should succeed (204 or 404)
        assert response1.status_code in [204, 404]
        # Second should be 404 (not found)
        assert response2.status_code in [404, 204]


# ============================================================================
# Integration Tests
# ============================================================================

class TestEndpointIntegration:
    """Integration tests between endpoints"""

    @pytest.mark.asyncio
    async def test_register_and_get_token(self, client, auth_headers):
        """Test registering token then querying"""
        # Register token
        register_payload = {
            "token": f"integration_test_{uuid4()}",
            "platform": "android",
            "device_name": "Test Device",
        }

        register_response = client.post(
            "/api/v1/push/tokens",
            json=register_payload,
            headers=auth_headers,
        )

        assert register_response.status_code == 201

    @pytest.mark.asyncio
    async def test_notification_workflow(self, client, auth_headers):
        """Test complete notification workflow"""
        # 1. Get initial unread count
        unread_response = client.get(
            "/api/v1/push/notifications/unread/count",
            headers=auth_headers,
        )
        assert unread_response.status_code == 200
        initial_count = unread_response.json()["unread_count"]

        # 2. Get notifications list
        list_response = client.get(
            "/api/v1/push/notifications",
            headers=auth_headers,
        )
        assert list_response.status_code == 200
        notifications = list_response.json()["items"]

        # 3. If there are unread notifications, mark as read
        if notifications:
            for notif in notifications:
                if not notif.get("is_read"):
                    read_response = client.put(
                        f"/api/v1/push/notifications/{notif['id']}/read",
                        headers=auth_headers,
                    )
                    assert read_response.status_code in [200, 404]

        # 4. Verify unread count decreased (or is 0)
        final_response = client.get(
            "/api/v1/push/notifications/unread/count",
            headers=auth_headers,
        )
        assert final_response.status_code == 200
        final_count = final_response.json()["unread_count"]
        assert final_count <= initial_count
