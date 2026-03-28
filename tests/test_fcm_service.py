"""FCM (Firebase Cloud Messaging) 서비스 테스트"""
import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch

from app.domain.push.services.fcm_service import FcmService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_firebase_init():
    with patch(
        'app.domain.push.services.fcm_service.initialize_firebase'
    ) as mock:
        yield mock


# ============================================================================
# Single Token Sending Tests
# ============================================================================

class TestFcmSingleTokenSending:
    """단일 토큰 FCM 전송 테스트"""

    @pytest.mark.asyncio
    async def test_send_to_token_success(self, mock_firebase_init):
        """단일 토큰 전송 성공"""
        token = str(uuid4())
        message_id = "test_message_id_123"

        with patch(
            'app.domain.push.services.fcm_service.messaging.send',
            return_value=message_id,
        ) as mock_send:
            result = await FcmService.send_to_token(
                token=token,
                title="테스트 제목",
                body="테스트 본문",
            )

        assert result == message_id
        assert mock_send.called

    @pytest.mark.asyncio
    async def test_send_to_token_with_data(self, mock_firebase_init):
        """데이터 포함 단일 토큰 전송"""
        token = str(uuid4())
        message_id = "test_message_id_456"

        data = {
            "event_type": "blog.post.created",
            "related_id": str(uuid4()),
        }

        with patch(
            'app.domain.push.services.fcm_service.messaging.send',
            return_value=message_id,
        ):
            result = await FcmService.send_to_token(
                token=token,
                title="새 글 알림",
                body="새로운 블로그 글이 올라왔습니다",
                data=data,
            )

        assert result == message_id

    @pytest.mark.asyncio
    async def test_send_to_token_failure(self, mock_firebase_init):
        """단일 토큰 전송 실패"""
        token = str(uuid4())

        with patch(
            'app.domain.push.services.fcm_service.messaging.send',
            side_effect=Exception("Invalid token"),
        ):
            result = await FcmService.send_to_token(
                token=token,
                title="테스트",
                body="테스트",
            )

        assert result is None


# ============================================================================
# Multicast Sending Tests
# ============================================================================

class TestFcmMulticastSending:
    """멀티캐스트 FCM 전송 테스트"""

    @pytest.mark.asyncio
    async def test_send_to_tokens_success(self, mock_firebase_init):
        """멀티캐스트 전송 성공"""
        tokens = [str(uuid4()) for _ in range(3)]

        with patch(
            'app.domain.push.services.fcm_service.messaging.send',
            side_effect=["msg_0", "msg_1", "msg_2"],
        ) as mock_send:
            result = await FcmService.send_to_tokens(
                tokens=tokens,
                title="멀티캐스트 테스트",
                body="여러 사용자에게 전송",
            )

        assert result["success"] == 3
        assert result["failure"] == 0
        assert len(result["message_ids"]) == 3
        assert mock_send.call_count == 3

    @pytest.mark.asyncio
    async def test_send_to_tokens_partial_failure(self, mock_firebase_init):
        """멀티캐스트 부분 실패"""
        tokens = [str(uuid4()) for _ in range(3)]

        with patch(
            'app.domain.push.services.fcm_service.messaging.send',
            side_effect=["msg_0", Exception("Invalid token"), "msg_2"],
        ):
            result = await FcmService.send_to_tokens(
                tokens=tokens,
                title="부분 실패 테스트",
                body="2개 성공, 1개 실패",
            )

        assert result["success"] == 2
        assert result["failure"] == 1
        assert len(result["message_ids"]) == 2

    @pytest.mark.asyncio
    async def test_send_to_tokens_empty_list(self, mock_firebase_init):
        """빈 토큰 리스트 전송"""
        result = await FcmService.send_to_tokens(
            tokens=[],
            title="빈 리스트",
            body="아무도 없음",
        )

        assert result["success"] == 0
        assert result["failure"] == 0
        assert len(result["message_ids"]) == 0

    @pytest.mark.asyncio
    async def test_send_to_tokens_failure(self, mock_firebase_init):
        """멀티캐스트 전송 실패"""
        tokens = [str(uuid4()) for _ in range(2)]

        with patch(
            'app.domain.push.services.fcm_service.messaging.send',
            side_effect=Exception("Service unavailable"),
        ):
            result = await FcmService.send_to_tokens(
                tokens=tokens,
                title="테스트",
                body="테스트",
            )

        assert result["success"] == 0
        assert result["failure"] == 2
        assert len(result["message_ids"]) == 0


# ============================================================================
# Topic Sending Tests
# ============================================================================

class TestFcmTopicSending:
    """Topic 기반 FCM 전송 테스트"""

    @pytest.mark.asyncio
    async def test_send_to_topic_success(self, mock_firebase_init):
        """Topic 전송 성공"""
        topic = "news"
        message_id = "topic_message_123"

        with patch(
            'app.domain.push.services.fcm_service.messaging.send',
            return_value=message_id,
        ):
            result = await FcmService.send_to_topic(
                topic=topic,
                title="뉴스",
                body="새로운 뉴스입니다",
            )

        assert result == message_id

    @pytest.mark.asyncio
    async def test_send_to_topic_with_data(self, mock_firebase_init):
        """데이터 포함 Topic 전송"""
        topic = "promotions"
        message_id = "promo_message_456"

        data = {
            "promo_code": "SAVE10",
            "discount": "10%",
        }

        with patch(
            'app.domain.push.services.fcm_service.messaging.send',
            return_value=message_id,
        ):
            result = await FcmService.send_to_topic(
                topic=topic,
                title="프로모션",
                body="할인 이벤트",
                data=data,
            )

        assert result == message_id

    @pytest.mark.asyncio
    async def test_send_to_topic_failure(self, mock_firebase_init):
        """Topic 전송 실패"""

        with patch(
            'app.domain.push.services.fcm_service.messaging.send',
            side_effect=Exception("Topic not found"),
        ):
            result = await FcmService.send_to_topic(
                topic="invalid_topic",
                title="테스트",
                body="테스트",
            )

        assert result is None


# ============================================================================
# Topic Management Tests
# ============================================================================

class TestFcmTopicManagement:
    """Topic 구독/구독해제 테스트"""

    @pytest.mark.asyncio
    async def test_subscribe_to_topic_success(self, mock_firebase_init):
        """Topic 구독 성공"""
        tokens = [str(uuid4()) for _ in range(2)]
        topic = "updates"

        with patch(
            'app.domain.push.services.fcm_service.messaging.subscribe_to_topic'
        ) as mock_subscribe:
            result = await FcmService.subscribe_to_topic(tokens, topic)

        assert result is True
        assert mock_subscribe.called

    @pytest.mark.asyncio
    async def test_subscribe_to_topic_failure(self, mock_firebase_init):
        """Topic 구독 실패"""
        tokens = [str(uuid4())]
        topic = "updates"

        with patch(
            'app.domain.push.services.fcm_service.messaging.subscribe_to_topic',
            side_effect=Exception("Invalid token list"),
        ):
            result = await FcmService.subscribe_to_topic(tokens, topic)

        assert result is False

    @pytest.mark.asyncio
    async def test_unsubscribe_from_topic_success(self, mock_firebase_init):
        """Topic 구독해제 성공"""
        tokens = [str(uuid4()) for _ in range(2)]
        topic = "updates"

        with patch(
            'app.domain.push.services.fcm_service.messaging.unsubscribe_from_topic'
        ) as mock_unsubscribe:
            result = await FcmService.unsubscribe_from_topic(tokens, topic)

        assert result is True
        assert mock_unsubscribe.called

    @pytest.mark.asyncio
    async def test_unsubscribe_from_topic_failure(self, mock_firebase_init):
        """Topic 구독해제 실패"""
        tokens = [str(uuid4())]
        topic = "updates"

        with patch(
            'app.domain.push.services.fcm_service.messaging.unsubscribe_from_topic',
            side_effect=Exception("Topic management failed"),
        ):
            result = await FcmService.unsubscribe_from_topic(tokens, topic)

        assert result is False
