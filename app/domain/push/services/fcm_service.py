"""FCM (Firebase Cloud Messaging) 서비스"""
from typing import List, Dict, Optional
from firebase_admin import messaging
from app.core.fcm import initialize_firebase
import logging

logger = logging.getLogger(__name__)


class FcmService:
    """Firebase Cloud Messaging 서비스"""

    @staticmethod
    def _mask_token(token: str) -> str:
        if not token:
            return "<empty>"
        if len(token) <= 10:
            return "***"
        return f"{token[:6]}...{token[-4:]}"

    @staticmethod
    async def send_to_token(
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """단일 사용자에게 FCM으로 메시지 전송

        Args:
            token: FCM 토큰
            title: 알림 제목
            body: 알림 본문
            data: 추가 데이터 (딕셔너리)

        Returns:
            메시지 ID (성공 시) 또는 None (실패 시)
        """
        masked = FcmService._mask_token(token)
        try:
            initialize_firebase()

            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                token=token,
            )

            response = messaging.send(message)
            logger.info(f"FCM message sent to {masked}: {response}")
            return response

        except Exception as e:
            logger.error(f"Failed to send FCM message to {masked}: {str(e)}")
            return None

    @staticmethod
    async def send_to_tokens(
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """여러 사용자에게 FCM으로 메시지 전송 (멀티캐스트)

        Args:
            tokens: FCM 토큰 리스트
            title: 알림 제목
            body: 알림 본문
            data: 추가 데이터 (딕셔너리)

        Returns:
            결과 딕셔너리: {"success": int, "failure": int, "message_ids": [str]}
        """
        if not tokens:
            return {"success": 0, "failure": 0, "message_ids": []}

        message_ids = []
        success_count = 0
        failure_count = 0

        try:
            initialize_firebase()

            for token in tokens:
                message = messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data=data or {},
                    token=token,
                )
                try:
                    message_id = messaging.send(message)
                    message_ids.append(message_id)
                    success_count += 1
                except Exception as send_error:
                    failure_count += 1
                    logger.error(
                        "Failed to send FCM message to %s: %s",
                        FcmService._mask_token(token),
                        send_error,
                    )

            result = {
                "success": success_count,
                "failure": failure_count,
                "message_ids": message_ids,
            }
            logger.info(
                f"FCM multicast sent to {len(tokens)} users: "
                f"success={success_count}, failure={failure_count}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to send multicast FCM message: {str(e)}")
            return {"success": 0, "failure": len(tokens), "message_ids": []}

    @staticmethod
    async def send_to_topic(
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """Topic을 구독한 사용자들에게 FCM으로 메시지 전송

        Args:
            topic: FCM Topic 이름
            title: 알림 제목
            body: 알림 본문
            data: 추가 데이터 (딕셔너리)

        Returns:
            메시지 ID (성공 시) 또는 None (실패 시)
        """
        try:
            initialize_firebase()

            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                topic=topic,
            )

            response = messaging.send(message)
            logger.info(f"FCM message sent to topic {topic}: {response}")
            return response

        except Exception as e:
            logger.error(f"Failed to send FCM message to topic {topic}: {str(e)}")
            return None

    @staticmethod
    async def subscribe_to_topic(tokens: List[str], topic: str) -> bool:
        """토큰들을 Topic에 구독

        Args:
            tokens: FCM 토큰 리스트
            topic: Topic 이름

        Returns:
            성공 여부
        """
        try:
            initialize_firebase()
            messaging.subscribe_to_topic(tokens, topic)
            logger.info(f"Subscribed {len(tokens)} tokens to topic {topic}")
            return True

        except Exception as e:
            logger.error(f"Failed to subscribe tokens to topic {topic}: {str(e)}")
            return False

    @staticmethod
    async def unsubscribe_from_topic(tokens: List[str], topic: str) -> bool:
        """토큰들을 Topic에서 구독 해제

        Args:
            tokens: FCM 토큰 리스트
            topic: Topic 이름

        Returns:
            성공 여부
        """
        try:
            initialize_firebase()
            messaging.unsubscribe_from_topic(tokens, topic)
            logger.info(f"Unsubscribed {len(tokens)} tokens from topic {topic}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to unsubscribe tokens from topic {topic}: {str(e)}"
            )
            return False
