"""포인트 도메인 이벤트 핸들러"""
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.events import (
    UserCreatedEvent,
    PointsChargedEvent,
    PointsConsumedEvent,
    PointsRefundedEvent,
    event_bus,
)
from app.core.database import get_db
from app.domain.points.services.point_service import PointService

logger = logging.getLogger(__name__)


class PointsEventHandlers:
    """포인트 이벤트 핸들러"""

    @staticmethod
    async def handle_user_created(event: UserCreatedEvent, db: AsyncSession):
        """신규 사용자 생성 이벤트 처리

        - 가입 보너스 100포인트 충전

        Args:
            event: UserCreatedEvent
            db: AsyncSession
        """
        user_id_str = event.payload["user_id"]
        logger.info(f"🎉 신규 사용자 생성: user_id={user_id_str}")

        try:
            # UUID로 변환
            user_id = UUID(user_id_str) if isinstance(user_id_str, str) else user_id_str

            # 가입 보너스 100포인트 충전
            point_service = PointService(db)
            await point_service.charge(
                user_id=user_id,
                amount=100,
                description="가입 보너스",
                idempotency_key=f"welcome_{user_id}",
            )

            logger.info(f"✅ 가입 보너스 지급 완료: user_id={user_id}")

        except Exception as e:
            await db.rollback()
            logger.error(f"❌ 가입 보너스 지급 실패: user_id={user_id_str}, error={str(e)}")

    @staticmethod
    async def handle_points_charged(event: PointsChargedEvent, db: AsyncSession):
        """포인트 충전 이벤트 처리

        Args:
            event: PointsChargedEvent
            db: AsyncSession
        """
        user_id = event.payload["user_id"]
        amount = event.payload["amount"]
        balance = event.payload["balance_after"]
        description = event.payload["description"]

        logger.info(
            f"💰 포인트 충전: user_id={user_id}, "
            f"amount={amount}, balance={balance}, desc={description}"
        )

    @staticmethod
    async def handle_points_consumed(event: PointsConsumedEvent, db: AsyncSession):
        """포인트 사용 이벤트 처리

        Args:
            event: PointsConsumedEvent
            db: AsyncSession
        """
        user_id = event.payload["user_id"]
        amount = event.payload["amount"]
        balance = event.payload["balance_after"]
        description = event.payload["description"]

        logger.info(
            f"📉 포인트 사용: user_id={user_id}, "
            f"amount={amount}, balance={balance}, desc={description}"
        )

    @staticmethod
    async def handle_points_refunded(event: PointsRefundedEvent, db: AsyncSession):
        """포인트 환급 이벤트 처리

        Args:
            event: PointsRefundedEvent
            db: AsyncSession
        """
        user_id = event.payload["user_id"]
        amount = event.payload["amount"]
        balance = event.payload["balance_after"]
        description = event.payload["description"]

        logger.info(
            f"🔄 포인트 환급: user_id={user_id}, "
            f"amount={amount}, balance={balance}, desc={description}"
        )


async def register_points_event_handlers(event_bus) -> None:
    """포인트 이벤트 핸들러 등록

    Args:
        event_bus: 이벤트 버스
    """
    async for db in get_db():
        # 이벤트 핸들러 등록
        event_bus.subscribe(
            "user.created",
            lambda evt: PointsEventHandlers.handle_user_created(evt, db),
        )
        event_bus.subscribe(
            "points.charged",
            lambda evt: PointsEventHandlers.handle_points_charged(evt, db),
        )
        event_bus.subscribe(
            "points.consumed",
            lambda evt: PointsEventHandlers.handle_points_consumed(evt, db),
        )
        event_bus.subscribe(
            "points.refunded",
            lambda evt: PointsEventHandlers.handle_points_refunded(evt, db),
        )
        break

    logger.info("✅ 포인트 이벤트 핸들러 등록 완료")
