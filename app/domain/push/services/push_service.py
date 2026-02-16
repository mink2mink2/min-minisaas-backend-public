"""푸시 알림 서비스"""
from uuid import UUID
from typing import List, Optional, Tuple
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete, update

from app.domain.push.models.fcm_token import FcmToken
from app.domain.push.models.push_notification import PushNotification
from app.domain.push.services.fcm_service import FcmService
from app.core.config import settings

logger = logging.getLogger(__name__)


class PushService:
    """푸시 알림 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================================
    # FCM Token Management
    # ============================================================================

    async def register_token(
        self,
        user_id: UUID,
        token: str,
        platform: str,
        device_name: Optional[str] = None,
    ) -> FcmToken:
        """FCM 토큰 등록"""
        # 중복 확인 - 같은 토큰이 이미 존재하면 활성화
        result = await self.db.execute(
            select(FcmToken).where(FcmToken.token == token)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # 기존 토큰 업데이트
            existing.is_active = True
            existing.device_name = device_name
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        # 새로운 토큰 추가
        fcm_token = FcmToken(
            user_id=user_id,
            token=token.strip(),
            platform=platform.lower(),
            device_name=device_name.strip() if device_name else None,
            is_active=True,
        )
        self.db.add(fcm_token)
        await self.db.commit()
        await self.db.refresh(fcm_token)

        logger.info(f"FCM token registered for user {user_id}: {platform}")
        return fcm_token

    async def update_token(
        self,
        user_id: UUID,
        token: str,
        platform: str,
    ) -> Optional[FcmToken]:
        """FCM 토큰 업데이트"""
        result = await self.db.execute(
            select(FcmToken).where(
                and_(
                    FcmToken.user_id == user_id,
                    FcmToken.token == token,
                )
            )
        )
        fcm_token = result.scalar_one_or_none()

        if fcm_token:
            fcm_token.is_active = True
            fcm_token.platform = platform.lower()
            await self.db.commit()
            await self.db.refresh(fcm_token)
            return fcm_token

        return None

    async def remove_token(self, token: str) -> bool:
        """FCM 토큰 제거"""
        result = await self.db.execute(
            select(FcmToken).where(FcmToken.token == token)
        )
        fcm_token = result.scalar_one_or_none()

        if fcm_token:
            await self.db.delete(fcm_token)
            await self.db.commit()
            return True

        return False

    async def remove_user_tokens(self, user_id: UUID) -> int:
        """사용자의 모든 FCM 토큰 제거 (로그아웃 시)"""
        result = await self.db.execute(
            delete(FcmToken).where(FcmToken.user_id == user_id)
        )
        await self.db.commit()
        return result.rowcount

    async def deactivate_user_tokens(self, user_id: UUID) -> int:
        """사용자의 모든 FCM 토큰 비활성화"""
        result = await self.db.execute(
            update(FcmToken)
            .where(FcmToken.user_id == user_id)
            .values(is_active=False)
        )
        await self.db.commit()
        return result.rowcount

    async def get_user_tokens(self, user_id: UUID) -> List[FcmToken]:
        """사용자의 모든 활성 FCM 토큰 조회"""
        result = await self.db.execute(
            select(FcmToken).where(
                and_(
                    FcmToken.user_id == user_id,
                    FcmToken.is_active.is_(True),
                )
            )
        )
        return result.scalars().all()

    async def get_user_tokens_for_platform(
        self,
        user_id: UUID,
        platform: str,
    ) -> List[FcmToken]:
        """특정 플랫폼의 사용자 FCM 토큰 조회"""
        result = await self.db.execute(
            select(FcmToken).where(
                and_(
                    FcmToken.user_id == user_id,
                    FcmToken.platform == platform.lower(),
                    FcmToken.is_active.is_(True),
                )
            )
        )
        return result.scalars().all()

    # ============================================================================
    # Push Notification Sending
    # ============================================================================

    async def notify_user(
        self,
        user_id: UUID,
        title: str,
        body: str,
        event_type: Optional[str] = None,
        related_id: Optional[UUID] = None,
    ) -> PushNotification:
        """사용자에게 알림 발송 (DB + FCM)"""
        notification = PushNotification(
            user_id=user_id,
            title=title.strip(),
            body=body.strip(),
            event_type=event_type,
            related_id=related_id,
            sent_at=datetime.utcnow(),
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)

        # FCM으로도 전송
        try:
            # 사용자의 활성 FCM 토큰 조회
            user_tokens = await self.get_user_tokens(user_id)
            if user_tokens:
                tokens = [token.token for token in user_tokens]
                data = {
                    "event_type": event_type or "",
                    "related_id": str(related_id) if related_id else "",
                }
                await FcmService.send_to_tokens(tokens, title.strip(), body.strip(), data)
                logger.info(
                    f"FCM notification sent to user {user_id}: {event_type} ({len(tokens)} tokens)"
                )
        except Exception as e:
            logger.error(f"Failed to send FCM notification: {str(e)}")

        logger.info(
            f"Push notification sent to user {user_id}: {event_type}"
        )
        return notification

    async def notify_users(
        self,
        user_ids: List[UUID],
        title: str,
        body: str,
        event_type: Optional[str] = None,
        related_id: Optional[UUID] = None,
    ) -> int:
        """여러 사용자에게 알림 발송 (DB + FCM)"""
        if not user_ids:
            return 0

        notifications = [
            PushNotification(
                user_id=uid,
                title=title.strip(),
                body=body.strip(),
                event_type=event_type,
                related_id=related_id,
                sent_at=datetime.utcnow(),
            )
            for uid in user_ids
        ]

        self.db.add_all(notifications)
        await self.db.commit()

        # FCM으로도 전송
        try:
            all_tokens = []
            for user_id in user_ids:
                user_tokens = await self.get_user_tokens(user_id)
                all_tokens.extend([token.token for token in user_tokens])

            if all_tokens:
                data = {
                    "event_type": event_type or "",
                    "related_id": str(related_id) if related_id else "",
                }
                result = await FcmService.send_to_tokens(
                    all_tokens, title.strip(), body.strip(), data
                )
                logger.info(
                    f"FCM notifications sent to {len(user_ids)} users: "
                    f"{event_type} (success={result['success']}, failure={result['failure']})"
                )
        except Exception as e:
            logger.error(f"Failed to send FCM notifications: {str(e)}")

        logger.info(
            f"Push notifications sent to {len(notifications)} users: {event_type}"
        )
        return len(notifications)

    async def notify_subscribers(
        self,
        author_id: UUID,
        title: str,
        body: str,
        event_type: Optional[str] = None,
        related_id: Optional[UUID] = None,
    ) -> int:
        """구독자들에게 알림 발송 (블로그 구독자 등, DB + FCM)"""
        from app.domain.blog.models.subscription import BlogSubscription

        # 구독자 목록 조회
        result = await self.db.execute(
            select(BlogSubscription.subscriber_id).where(
                BlogSubscription.author_id == author_id
            )
        )
        subscriber_ids = [row[0] for row in result.all()]

        if not subscriber_ids:
            return 0

        # 알림 발송 (notify_users에서 FCM도 처리됨)
        return await self.notify_users(
            subscriber_ids,
            title,
            body,
            event_type,
            related_id,
        )

    # ============================================================================
    # Notification History
    # ============================================================================

    async def get_notifications(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[PushNotification], int]:
        """사용자의 알림 목록"""
        # 총 개수
        count_result = await self.db.execute(
            select(func.count())
            .select_from(PushNotification)
            .where(PushNotification.user_id == user_id)
        )
        total = count_result.scalar() or 0

        # 페이징된 결과
        offset = (page - 1) * limit
        result = await self.db.execute(
            select(PushNotification)
            .where(PushNotification.user_id == user_id)
            .order_by(PushNotification.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        notifications = result.scalars().all()

        return list(notifications), total

    async def get_unread_count(self, user_id: UUID) -> int:
        """사용자의 읽지 않은 알림 개수"""
        result = await self.db.execute(
            select(func.count())
            .select_from(PushNotification)
            .where(
                and_(
                    PushNotification.user_id == user_id,
                    PushNotification.is_read.is_(False),
                )
            )
        )
        return result.scalar() or 0

    async def mark_as_read(self, notification_id: UUID) -> bool:
        """알림을 읽음으로 표시"""
        result = await self.db.execute(
            select(PushNotification).where(PushNotification.id == notification_id)
        )
        notification = result.scalar_one_or_none()

        if not notification:
            return False

        notification.is_read = True
        await self.db.commit()
        return True

    async def mark_all_as_read(self, user_id: UUID) -> int:
        """사용자의 모든 알림을 읽음으로 표시"""
        result = await self.db.execute(
            update(PushNotification)
            .where(
                and_(
                    PushNotification.user_id == user_id,
                    PushNotification.is_read.is_(False),
                )
            )
            .values(is_read=True)
        )
        await self.db.commit()
        return result.rowcount

    async def delete_notification(self, notification_id: UUID) -> bool:
        """알림 삭제"""
        result = await self.db.execute(
            select(PushNotification).where(PushNotification.id == notification_id)
        )
        notification = result.scalar_one_or_none()

        if not notification:
            return False

        await self.db.delete(notification)
        await self.db.commit()
        return True

    async def delete_old_notifications(self, days: int = 30) -> int:
        """오래된 알림 삭제"""
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            delete(PushNotification).where(
                PushNotification.created_at < cutoff_date
            )
        )
        await self.db.commit()
        return result.rowcount
