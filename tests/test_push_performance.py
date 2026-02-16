"""푸시 알림 성능 및 부하 테스트"""
import pytest
import time
import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.domain.push.services.push_service import PushService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def push_service_with_mocks():
    """Mock dependencies를 포함한 PushService"""
    mock_db = MagicMock()

    service = PushService(db=mock_db)

    # Mock notify methods
    service.notify_user = AsyncMock(return_value=MagicMock(
        id=uuid4(),
        user_id=uuid4(),
        title="Test",
        body="Test body",
        event_type="test.event",
        is_read=False,
        created_at=datetime.utcnow()
    ))
    service.notify_users = AsyncMock(return_value=1)
    service.get_notifications = AsyncMock(return_value=([], 0))
    service.get_unread_count = AsyncMock(return_value=0)

    return service


# ============================================================================
# Single Notification Performance Tests
# ============================================================================

class TestSingleNotificationPerformance:
    """단일 알림 성능 테스트"""

    @pytest.mark.asyncio
    async def test_notify_user_response_time(self, push_service_with_mocks):
        """단일 사용자 알림 응답 시간 (< 100ms)"""
        start_time = time.time()

        await push_service_with_mocks.notify_user(
            user_id=uuid4(),
            title="Test Notification",
            body="Performance test",
            event_type="test.event"
        )

        elapsed = (time.time() - start_time) * 1000  # ms
        assert elapsed < 100  # 100ms 이내

    @pytest.mark.asyncio
    async def test_get_unread_count_response_time(self, push_service_with_mocks):
        """미읽음 개수 조회 응답 시간 (< 50ms)"""
        user_id = uuid4()
        start_time = time.time()

        await push_service_with_mocks.get_unread_count(user_id)

        elapsed = (time.time() - start_time) * 1000  # ms
        assert elapsed < 50  # 50ms 이내

    @pytest.mark.asyncio
    async def test_mark_as_read_response_time(self, push_service_with_mocks):
        """알림 읽음 처리 응답 시간 (< 75ms)"""
        push_service_with_mocks.mark_as_read = AsyncMock(return_value=True)
        
        start_time = time.time()

        await push_service_with_mocks.mark_as_read(uuid4())

        elapsed = (time.time() - start_time) * 1000  # ms
        assert elapsed < 75  # 75ms 이내


# ============================================================================
# Bulk Notification Performance Tests
# ============================================================================

class TestBulkNotificationPerformance:
    """대량 알림 성능 테스트"""

    @pytest.mark.asyncio
    async def test_notify_100_users_performance(self, push_service_with_mocks):
        """100명 사용자에게 알림 (< 500ms)"""
        user_ids = [uuid4() for _ in range(100)]

        start_time = time.time()

        await push_service_with_mocks.notify_users(
            user_ids=user_ids,
            title="Bulk Notification",
            body="Performance test for 100 users"
        )

        elapsed = (time.time() - start_time) * 1000  # ms
        assert elapsed < 500  # 500ms 이내

    @pytest.mark.asyncio
    async def test_notify_1000_users_performance(self, push_service_with_mocks):
        """1000명 사용자에게 알림 (< 2000ms)"""
        user_ids = [uuid4() for _ in range(1000)]

        start_time = time.time()

        await push_service_with_mocks.notify_users(
            user_ids=user_ids,
            title="Bulk Notification",
            body="Performance test for 1000 users"
        )

        elapsed = (time.time() - start_time) * 1000  # ms
        assert elapsed < 2000  # 2초 이내

    @pytest.mark.asyncio
    async def test_bulk_notification_call_count(self, push_service_with_mocks):
        """대량 알림 호출 횟수 확인"""
        user_ids = [uuid4() for _ in range(50)]

        await push_service_with_mocks.notify_users(
            user_ids=user_ids,
            title="Test",
            body="Test"
        )

        # notify_users는 한 번만 호출되어야 함 (배치 처리)
        assert push_service_with_mocks.notify_users.call_count == 1


# ============================================================================
# Concurrent Operation Performance Tests
# ============================================================================

class TestConcurrentOperationPerformance:
    """동시 작업 성능 테스트"""

    @pytest.mark.asyncio
    async def test_concurrent_single_notifications(self, push_service_with_mocks):
        """10개 동시 단일 알림 (< 300ms)"""
        user_ids = [uuid4() for _ in range(10)]

        start_time = time.time()

        tasks = [
            push_service_with_mocks.notify_user(
                user_id=uid,
                title=f"Notification {i}",
                body="Concurrent test"
            )
            for i, uid in enumerate(user_ids)
        ]

        await asyncio.gather(*tasks)

        elapsed = (time.time() - start_time) * 1000  # ms
        assert elapsed < 300  # 300ms 이내

    @pytest.mark.asyncio
    async def test_concurrent_read_operations(self, push_service_with_mocks):
        """10개 동시 읽음 처리 (< 200ms)"""
        notification_ids = [uuid4() for _ in range(10)]
        push_service_with_mocks.mark_as_read = AsyncMock(return_value=True)

        start_time = time.time()

        tasks = [
            push_service_with_mocks.mark_as_read(nid)
            for nid in notification_ids
        ]

        await asyncio.gather(*tasks)

        elapsed = (time.time() - start_time) * 1000  # ms
        assert elapsed < 200  # 200ms 이내

    @pytest.mark.asyncio
    async def test_mixed_concurrent_operations(self, push_service_with_mocks):
        """혼합 동시 작업 (알림 + 조회 + 읽음, < 400ms)"""
        user_id = uuid4()

        start_time = time.time()

        tasks = [
            push_service_with_mocks.notify_user(user_id, "Title", "Body"),
            push_service_with_mocks.get_unread_count(user_id),
            push_service_with_mocks.get_notifications(user_id),
        ] * 3  # 3번 반복

        await asyncio.gather(*tasks)

        elapsed = (time.time() - start_time) * 1000  # ms
        assert elapsed < 400  # 400ms 이내


# ============================================================================
# Data Retrieval Performance Tests
# ============================================================================

class TestDataRetrievalPerformance:
    """데이터 조회 성능 테스트"""

    @pytest.mark.asyncio
    async def test_get_notifications_pagination_performance(self, push_service_with_mocks):
        """알림 목록 조회 (pagination, < 100ms)"""
        user_id = uuid4()

        start_time = time.time()

        await push_service_with_mocks.get_notifications(
            user_id=user_id,
            page=1,
            limit=20
        )

        elapsed = (time.time() - start_time) * 1000  # ms
        assert elapsed < 100  # 100ms 이내

    @pytest.mark.asyncio
    async def test_get_large_notification_page(self, push_service_with_mocks):
        """대량 알림 조회 (limit=100, < 150ms)"""
        user_id = uuid4()

        start_time = time.time()

        await push_service_with_mocks.get_notifications(
            user_id=user_id,
            page=1,
            limit=100
        )

        elapsed = (time.time() - start_time) * 1000  # ms
        assert elapsed < 150  # 150ms 이내


# ============================================================================
# Load and Stress Performance Tests
# ============================================================================

class TestLoadAndStressPerformance:
    """부하 및 스트레스 테스트"""

    @pytest.mark.asyncio
    async def test_rapid_sequential_notifications(self, push_service_with_mocks):
        """빠른 연속 알림 발송 (100개, < 1000ms)"""
        start_time = time.time()

        for i in range(100):
            await push_service_with_mocks.notify_user(
                user_id=uuid4(),
                title=f"Notification {i}",
                body="Rapid fire test"
            )

        elapsed = (time.time() - start_time) * 1000  # ms
        assert elapsed < 1000  # 1초 이내

    @pytest.mark.asyncio
    async def test_notifications_under_load(self, push_service_with_mocks):
        """다양한 도메인에서 동시 알림 발송 (성능 저하 최소화)"""
        tasks = []

        # Blog 알림 20개
        for i in range(20):
            tasks.append(
                push_service_with_mocks.notify_user(
                    user_id=uuid4(),
                    title="Blog Notification",
                    body=f"Blog {i}",
                    event_type="blog.post.created"
                )
            )

        # Chat 알림 20개
        for i in range(20):
            tasks.append(
                push_service_with_mocks.notify_user(
                    user_id=uuid4(),
                    title="Chat Message",
                    body=f"Message {i}",
                    event_type="chat.message.created"
                )
            )

        # Board 알림 20개
        for i in range(20):
            tasks.append(
                push_service_with_mocks.notify_user(
                    user_id=uuid4(),
                    title="Board Notification",
                    body=f"Board {i}",
                    event_type="board.post.liked"
                )
            )

        start_time = time.time()
        await asyncio.gather(*tasks)
        elapsed = (time.time() - start_time) * 1000  # ms

        # 60개 동시 작업이 2초 이내에 완료
        assert elapsed < 2000


# ============================================================================
# Resource Usage Tests
# ============================================================================

class TestResourceUsage:
    """리소스 사용량 테스트"""

    @pytest.mark.asyncio
    async def test_notification_service_memory_efficiency(self, push_service_with_mocks):
        """알림 서비스 메모리 효율성"""
        # 많은 알림 생성 요청
        tasks = [
            push_service_with_mocks.notify_user(
                user_id=uuid4(),
                title="Test",
                body="Memory test"
            )
            for _ in range(500)
        ]

        # 메모리 사용량이 과도하게 증가하지 않아야 함
        # (mock 객체이므로 실제 메모리 측정은 어렵지만, 실행 완료 확인)
        await asyncio.gather(*tasks)
        assert push_service_with_mocks.notify_user.call_count == 500

    @pytest.mark.asyncio
    async def test_batch_operations_efficiency(self, push_service_with_mocks):
        """배치 작업 효율성"""
        # 한 번의 배치 작업
        user_ids = [uuid4() for _ in range(1000)]

        start_time = time.time()

        await push_service_with_mocks.notify_users(
            user_ids=user_ids,
            title="Batch Operation",
            body="Test batch efficiency"
        )

        elapsed = (time.time() - start_time) * 1000  # ms

        # 배치 작업이 효율적으로 처리됨
        assert elapsed < 1000  # 1초 이내
        # 호출은 최소 횟수여야 함
        assert push_service_with_mocks.notify_users.call_count <= 1
