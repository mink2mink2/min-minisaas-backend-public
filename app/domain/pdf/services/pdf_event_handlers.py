"""PDF 도메인 이벤트 핸들러

책임:
- PDF 이벤트 수신 및 처리
- 포인트 차감
- 알림 발행
- 로깅
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.events import (
    PDFFileCreatedEvent,
    PDFConversionCompletedEvent,
    PDFFileDeletedEvent,
    Event,
)
from app.models.transaction import Transaction
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
        user_id = event.payload["user_id"]
        conversion_cost = event.payload["conversion_cost"]

        logger.info(
            f"✅ PDF 변환 완료: "
            f"user_id={user_id}, "
            f"file_id={event.payload['file_id']}, "
            f"cost={conversion_cost}"
        )

        if conversion_cost > 0:
            try:
                # TODO: Points Service 호출해서 포인트 차감
                # 1. User 포인트 업데이트
                # 2. Transaction 기록
                # 3. EventLog 기록

                logger.info(
                    f"💰 포인트 차감: user_id={user_id}, "
                    f"amount={conversion_cost}"
                )
            except Exception as e:
                logger.error(
                    f"❌ 포인트 차감 실패: user_id={user_id}, error={e}"
                )

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
