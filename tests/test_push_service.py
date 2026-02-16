"""푸시 알림 서비스 테스트"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.push.models.fcm_token import FcmToken
from app.domain.push.models.push_notification import PushNotification
from app.domain.push.services.push_service import PushService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Mock database session"""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def push_service(mock_db):
    """Push service instance with mock database"""
    return PushService(db=mock_db)


@pytest.fixture
def user_id():
    """Test user ID"""
    return uuid4()


@pytest.fixture
def fcm_token_data():
    """Sample FCM token data"""
    return {
        "token": "test_fcm_token_abc123",
        "platform": "android",
        "device_name": "Samsung S21",
    }


# ============================================================================
# Token Management Tests
# ============================================================================

class TestTokenManagement:
    """FCM token management tests"""

    @pytest.mark.asyncio
    async def test_register_token_new(self, push_service, user_id, fcm_token_data):
        """Test registering a new FCM token"""
        # Mock the database execute call
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        push_service.db.execute = AsyncMock(return_value=mock_result)
        push_service.db.commit = AsyncMock()
        push_service.db.refresh = AsyncMock()

        # Create token
        token = await push_service.register_token(
            user_id=user_id,
            token=fcm_token_data["token"],
            platform=fcm_token_data["platform"],
            device_name=fcm_token_data["device_name"],
        )

        # Verify database called
        assert push_service.db.add.called
        assert push_service.db.commit.called
        assert push_service.db.refresh.called

    @pytest.mark.asyncio
    async def test_register_token_duplicate(self, push_service, user_id):
        """Test registering duplicate token reactivates existing"""
        token_str = "duplicate_token"
        existing_token = FcmToken(
            id=uuid4(),
            user_id=user_id,
            token=token_str,
            platform="android",
            device_name="Device",
            is_active=False,
        )

        # Mock existing token lookup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_token
        push_service.db.execute = AsyncMock(return_value=mock_result)
        push_service.db.commit = AsyncMock()
        push_service.db.refresh = AsyncMock()

        # Register duplicate
        token = await push_service.register_token(
            user_id=user_id,
            token=token_str,
            platform="android",
        )

        # Verify token reactivated
        assert token.is_active is True

    @pytest.mark.asyncio
    async def test_update_token(self, push_service, user_id):
        """Test updating an FCM token"""
        token_id = str(uuid4())
        token_str = "test_token"
        existing_token = FcmToken(
            id=uuid4(),
            user_id=user_id,
            token=token_str,
            platform="ios",
            device_name="Device",
            is_active=True,
        )

        # Mock update
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_token
        push_service.db.execute = AsyncMock(return_value=mock_result)
        push_service.db.commit = AsyncMock()
        push_service.db.refresh = AsyncMock()

        # Update token
        token = await push_service.update_token(
            user_id=user_id,
            token=token_str,
            platform="android",
        )

        # Verify updated
        assert token is not None
        assert token.platform == "android"

    @pytest.mark.asyncio
    async def test_update_token_not_found(self, push_service, user_id):
        """Test updating non-existent token"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        push_service.db.execute = AsyncMock(return_value=mock_result)

        # Update non-existent
        token = await push_service.update_token(
            user_id=user_id,
            token="non_existent",
            platform="android",
        )

        # Verify returns None
        assert token is None

    @pytest.mark.asyncio
    async def test_remove_token(self, push_service):
        """Test removing an FCM token"""
        token_str = "test_token"
        existing_token = MagicMock(spec=FcmToken)

        # Mock token lookup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_token
        push_service.db.execute = AsyncMock(return_value=mock_result)
        push_service.db.delete = AsyncMock()
        push_service.db.commit = AsyncMock()

        # Remove token
        success = await push_service.remove_token(token_str)

        # Verify removed
        assert success is True
        assert push_service.db.delete.called

    @pytest.mark.asyncio
    async def test_remove_token_not_found(self, push_service):
        """Test removing non-existent token"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        push_service.db.execute = AsyncMock(return_value=mock_result)

        # Remove non-existent
        success = await push_service.remove_token("non_existent")

        # Verify returns False
        assert success is False

    @pytest.mark.asyncio
    async def test_remove_user_tokens(self, push_service, user_id):
        """Test removing all user tokens"""
        mock_result = MagicMock()
        mock_result.rowcount = 3
        push_service.db.execute = AsyncMock(return_value=mock_result)
        push_service.db.commit = AsyncMock()

        # Remove all
        count = await push_service.remove_user_tokens(user_id)

        # Verify count
        assert count == 3

    @pytest.mark.asyncio
    async def test_deactivate_user_tokens(self, push_service, user_id):
        """Test deactivating user tokens"""
        mock_result = MagicMock()
        mock_result.rowcount = 2
        push_service.db.execute = AsyncMock(return_value=mock_result)
        push_service.db.commit = AsyncMock()

        # Deactivate
        count = await push_service.deactivate_user_tokens(user_id)

        # Verify count
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_user_tokens(self, push_service, user_id):
        """Test getting active user tokens"""
        tokens = [
            FcmToken(
                id=uuid4(),
                user_id=user_id,
                token=f"token_{i}",
                platform="android",
                device_name=f"Device {i}",
                is_active=True,
            )
            for i in range(3)
        ]

        # Mock query
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = tokens
        mock_result.scalars.return_value = mock_scalars
        push_service.db.execute = AsyncMock(return_value=mock_result)

        # Get tokens
        result = await push_service.get_user_tokens(user_id)

        # Verify
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_user_tokens_for_platform(self, push_service, user_id):
        """Test getting platform-specific tokens"""
        tokens = [
            FcmToken(
                id=uuid4(),
                user_id=user_id,
                token="token_1",
                platform="android",
                device_name="Device 1",
                is_active=True,
            )
        ]

        # Mock query
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = tokens
        mock_result.scalars.return_value = mock_scalars
        push_service.db.execute = AsyncMock(return_value=mock_result)

        # Get tokens
        result = await push_service.get_user_tokens_for_platform(user_id, "android")

        # Verify
        assert len(result) == 1


# ============================================================================
# Notification Sending Tests
# ============================================================================

class TestNotificationSending:
    """Notification sending tests"""

    @pytest.mark.asyncio
    async def test_notify_user(self, push_service, user_id):
        """Test sending notification to single user"""
        push_service.db.add = MagicMock()
        push_service.db.commit = AsyncMock()
        push_service.db.refresh = AsyncMock()

        # Send notification
        notif = await push_service.notify_user(
            user_id=user_id,
            title="Test Title",
            body="Test Body",
            event_type="blog.post.created",
        )

        # Verify
        assert notif is not None
        assert push_service.db.add.called
        assert push_service.db.commit.called

    @pytest.mark.asyncio
    async def test_notify_users(self, push_service):
        """Test sending notifications to multiple users"""
        user_ids = [uuid4(), uuid4(), uuid4()]
        push_service.db.add_all = MagicMock()
        push_service.db.commit = AsyncMock()

        # Send notifications
        count = await push_service.notify_users(
            user_ids=user_ids,
            title="Test Title",
            body="Test Body",
        )

        # Verify
        assert count == 3
        assert push_service.db.add_all.called

    @pytest.mark.asyncio
    async def test_notify_users_empty_list(self, push_service):
        """Test sending notifications to empty list"""
        count = await push_service.notify_users(
            user_ids=[],
            title="Test",
            body="Test",
        )

        # Verify
        assert count == 0

    @pytest.mark.asyncio
    async def test_notify_subscribers(self, push_service, user_id):
        """Test sending notifications to subscribers"""
        subscriber_ids = [uuid4(), uuid4()]

        # Mock subscription query
        mock_result = MagicMock()
        mock_result.all.return_value = [(sub_id,) for sub_id in subscriber_ids]
        push_service.db.execute = AsyncMock(return_value=mock_result)

        # Mock notification creation
        push_service.db.add_all = MagicMock()
        push_service.db.commit = AsyncMock()

        # Send notifications
        count = await push_service.notify_subscribers(
            author_id=user_id,
            title="New Post",
            body="Author posted",
        )

        # Verify
        assert count == 2


# ============================================================================
# Notification History Tests
# ============================================================================

class TestNotificationHistory:
    """Notification history management tests"""

    @pytest.mark.asyncio
    async def test_get_notifications(self, push_service, user_id):
        """Test getting paginated notifications"""
        notifications = [
            PushNotification(
                id=uuid4(),
                user_id=user_id,
                title=f"Notification {i}",
                body=f"Body {i}",
                event_type="blog.post.created",
                is_read=False,
                created_at=datetime.utcnow(),
            )
            for i in range(5)
        ]

        # Mock count query
        count_result = MagicMock()
        count_result.scalar.return_value = 5

        # Mock notifications query
        notif_result = MagicMock()
        notif_scalars = MagicMock()
        notif_scalars.all.return_value = notifications
        notif_result.scalars.return_value = notif_scalars

        # Setup mock to return different values
        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return count_result
            else:
                return notif_result

        push_service.db.execute = AsyncMock(side_effect=mock_execute)

        # Get notifications
        result, total = await push_service.get_notifications(user_id, page=1, limit=20)

        # Verify
        assert total == 5
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_get_unread_count(self, push_service, user_id):
        """Test getting unread notification count"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        push_service.db.execute = AsyncMock(return_value=mock_result)

        # Get count
        count = await push_service.get_unread_count(user_id)

        # Verify
        assert count == 3

    @pytest.mark.asyncio
    async def test_mark_as_read(self, push_service):
        """Test marking notification as read"""
        notification_id = uuid4()
        notif = PushNotification(
            id=notification_id,
            user_id=uuid4(),
            title="Test",
            body="Test",
            is_read=False,
            created_at=datetime.utcnow(),
        )

        # Mock lookup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = notif
        push_service.db.execute = AsyncMock(return_value=mock_result)
        push_service.db.commit = AsyncMock()

        # Mark as read
        success = await push_service.mark_as_read(notification_id)

        # Verify
        assert success is True
        assert notif.is_read is True

    @pytest.mark.asyncio
    async def test_mark_all_as_read(self, push_service, user_id):
        """Test marking all notifications as read"""
        mock_result = MagicMock()
        mock_result.rowcount = 3
        push_service.db.execute = AsyncMock(return_value=mock_result)
        push_service.db.commit = AsyncMock()

        # Mark all
        count = await push_service.mark_all_as_read(user_id)

        # Verify
        assert count == 3

    @pytest.mark.asyncio
    async def test_delete_notification(self, push_service):
        """Test deleting notification"""
        notification_id = uuid4()
        notif = MagicMock(spec=PushNotification)

        # Mock lookup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = notif
        push_service.db.execute = AsyncMock(return_value=mock_result)
        push_service.db.delete = AsyncMock()
        push_service.db.commit = AsyncMock()

        # Delete
        success = await push_service.delete_notification(notification_id)

        # Verify
        assert success is True
        assert push_service.db.delete.called

    @pytest.mark.asyncio
    async def test_delete_old_notifications(self, push_service):
        """Test deleting old notifications"""
        mock_result = MagicMock()
        mock_result.rowcount = 10
        push_service.db.execute = AsyncMock(return_value=mock_result)
        push_service.db.commit = AsyncMock()

        # Delete old
        count = await push_service.delete_old_notifications(days=30)

        # Verify
        assert count == 10
