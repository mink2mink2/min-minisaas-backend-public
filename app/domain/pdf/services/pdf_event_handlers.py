"""PDF 도메인 이벤트 핸들러

책임:
- PDF 이벤트 수신 및 처리
- 포인트 차감
- 알림 발행
- 로깅
"""
import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.events import (
    PDFFileCreatedEvent,
    PDFConversionCompletedEvent,
    PDFFileDeletedEvent,
    Event,
)
from app.models.transaction import Transaction, TransactionType
from app.domain.auth.models.user import User
from app.core.database import get_db

logger = logging.getLogger(__name__)


class PDFEventHandlers:
    """PDF 이벤트 핸들러"""

    @staticmethod
    async def handle_pdf_file_created(event: PDFFileCreatedEvent, db: AsyncSession):
        """PDF 파일 생성 이벤트 처리

        Args:
            event: PDFFileCreatedEvent
            db: 데이터베이스 세션
        """
        logger.info(
            f"📤 PDF 파일 생성: "
            f"user_id={event.payload['user_id']}, "
            f"file_id={event.payload['file_id']}, "
            f"filename={event.payload['filename']}"
        )
        # TODO: 파일 생성 알림 발송

    @staticmethod
    async def handle_pdf_conversion_completed(
        event: PDFConversionCompletedEvent,
        db: AsyncSession,
    ):
        """PDF 변환 완료 이벤트 처리

        - 포인트 차감
        - 변환 완료 알림
        - 거래 기록

        Args:
            event: PDFConversionCompletedEvent
            db: 데이터베이스 세션
        """
        user_id_str = event.payload["user_id"]
        conversion_cost = event.payload["conversion_cost"]
        file_id = event.payload["file_id"]

        logger.info(
            f"✅ PDF 변환 완료: "
            f"user_id={user_id_str}, "
            f"file_id={file_id}, "
            f"cost={conversion_cost}"
        )

        if conversion_cost > 0:
            try:
                # Convert string user_id to UUID
                user_id = UUID(user_id_str) if isinstance(user_id_str, str) else user_id_str

                # 1. User의 포인트 조회
                user_query = select(User).where(User.id == user_id)
                user_result = await db.execute(user_query)
                user = user_result.scalar_one_or_none()

                if not user:
                    logger.error(f"❌ 사용자를 찾을 수 없음: user_id={user_id}")
                    return

                # 현재 포인트 (차감 전)
                current_points = user.points

                # 2. 포인트 차감 (음수 방지)
                new_points = max(0, current_points - conversion_cost)
                points_deducted = current_points - new_points

                # User 포인트 업데이트
                await db.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(points=new_points)
                )

                # 3. Transaction 레코드 생성 (감시 추적용)
                transaction = Transaction(
                    user_id=user_id,
                    type=TransactionType.CONSUME,
                    amount=points_deducted,
                    balance_after=new_points,
                    description=f"PDF 변환 비용 (file_id={file_id})",
                    idempotency_key=f"pdf_conversion_{file_id}",
                    prev_hash=None,  # TODO: 해시 체인 구현
                    current_hash="",  # TODO: 해시 체인 구현
                    tx_data=f"{{\"file_id\": \"{file_id}\", \"conversion_cost\": {conversion_cost}}}",
                )
                db.add(transaction)

                # 커밋
                await db.commit()

                logger.info(
                    f"💰 포인트 차감 완료: user_id={user_id}, "
                    f"deducted={points_deducted}, "
                    f"balance_before={current_points}, "
                    f"balance_after={new_points}"
                )
            except Exception as e:
                await db.rollback()
                logger.error(
                    f"❌ 포인트 차감 실패: user_id={user_id_str}, error={str(e)}"
                )
                # 에러가 발생해도 이벤트 처리는 계속 진행
                # (나중에 수동 개입이 필요할 수 있음)

        # TODO: 변환 완료 알림 발송

    @staticmethod
    async def handle_pdf_file_deleted(event: PDFFileDeletedEvent, db: AsyncSession):
        """PDF 파일 삭제 이벤트 처리

        Args:
            event: PDFFileDeletedEvent
            db: 데이터베이스 세션
        """
        logger.info(
            f"🗑️ PDF 파일 삭제: "
            f"user_id={event.payload['user_id']}, "
            f"file_id={event.payload['file_id']}"
        )
        # TODO: 파일 삭제 알림 발송


async def register_pdf_event_handlers(event_bus) -> None:
    """PDF 이벤트 핸들러 등록

    Args:
        event_bus: 이벤트 버스
    """
    # 데이터베이스 세션 가져오기
    async for db in get_db():
        # 이벤트 핸들러 등록
        event_bus.subscribe(
            "pdf.file.created",
            lambda evt: PDFEventHandlers.handle_pdf_file_created(evt, db),
        )
        event_bus.subscribe(
            "pdf.conversion.completed",
            lambda evt: PDFEventHandlers.handle_pdf_conversion_completed(evt, db),
        )
        event_bus.subscribe(
            "pdf.file.deleted",
            lambda evt: PDFEventHandlers.handle_pdf_file_deleted(evt, db),
        )
        break  # 한 번만 등록

    logger.info("✅ PDF 이벤트 핸들러 등록 완료")
