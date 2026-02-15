"""PDF 파일 관리 서비스

책임:
- CRUD 작업
- 파일 생명주기 관리
- 포인트 시스템 통합
- 이벤트 발행
"""
import logging
from typing import Optional, List
from datetime import datetime
from uuid import uuid4
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.pdf.models import PDFFile, FileStatus, FileType
from app.domain.pdf.schemas import PDFFileCreate, PDFFileUpdate
from app.core.events import EventBus

logger = logging.getLogger(__name__)


class PDFFileService:
    """PDF 파일 서비스

    Events:
    - PDFFileCreatedEvent
    - PDFFileStatusChangedEvent
    - PDFFileDeletedEvent
    """

    def __init__(self, db: AsyncSession, event_bus: Optional[EventBus] = None):
        self.db = db
        self.event_bus = event_bus

    async def create_pdf_file(
        self,
        user_id: int,
        data: PDFFileCreate,
        minio_bucket: str,
        minio_path: str,
    ) -> PDFFile:
        """PDF 파일 레코드 생성

        Args:
            user_id: 소유자 ID
            data: 생성 데이터
            minio_bucket: MinIO 버킷명
            minio_path: MinIO 경로

        Returns:
            생성된 PDFFile 객체
        """
        file_id = str(uuid4())

        pdf_file = PDFFile(
            file_id=file_id,
            user_id=user_id,
            original_filename=data.original_filename,
            file_type=data.file_type,
            status=FileStatus.UPLOADING,
            minio_bucket=minio_bucket,
            minio_path=minio_path,
            file_size_bytes=data.file_size_bytes,
        )

        self.db.add(pdf_file)
        await self.db.flush()

        logger.info(f"✅ PDF 파일 생성: {file_id}")

        # 이벤트 발행
        if self.event_bus:
            from app.core.events import PDFFileCreatedEvent
            await self.event_bus.emit(
                PDFFileCreatedEvent(
                    user_id=user_id,
                    file_id=file_id,
                    filename=data.original_filename,
                    file_size=data.file_size_bytes,
                )
            )

        return pdf_file

    async def get_pdf_file(self, file_id: str) -> Optional[PDFFile]:
        """파일 조회

        Args:
            file_id: 파일 ID

        Returns:
            PDFFile 또는 None
        """
        result = await self.db.execute(
            select(PDFFile).where(PDFFile.file_id == file_id)
        )
        return result.scalar_one_or_none()

    async def get_user_pdf_files(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        include_deleted: bool = False,
    ) -> List[PDFFile]:
        """사용자의 PDF 파일 목록 조회

        Args:
            user_id: 사용자 ID
            skip: 건너뛸 개수
            limit: 조회 개수
            include_deleted: 삭제된 파일 포함 여부

        Returns:
            PDFFile 목록
        """
        query = select(PDFFile).where(PDFFile.user_id == user_id)

        if not include_deleted:
            query = query.where(PDFFile.is_deleted == False)

        query = query.offset(skip).limit(limit).order_by(PDFFile.created_at.desc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_pdf_file(
        self,
        file_id: str,
        data: PDFFileUpdate,
    ) -> Optional[PDFFile]:
        """파일 정보 수정

        Args:
            file_id: 파일 ID
            data: 수정 데이터

        Returns:
            수정된 PDFFile 또는 None
        """
        pdf_file = await self.get_pdf_file(file_id)
        if not pdf_file:
            return None

        old_status = pdf_file.status
        update_dict = data.model_dump(exclude_unset=True)

        for key, value in update_dict.items():
            setattr(pdf_file, key, value)

        pdf_file.updated_at = datetime.utcnow()
        await self.db.flush()

        logger.info(f"✅ PDF 파일 수정: {file_id}")

        # 상태 변경 이벤트 발행
        if old_status != data.status and data.status and self.event_bus:
            from app.core.events import PDFFileStatusChangedEvent
            await self.event_bus.emit(
                PDFFileStatusChangedEvent(
                    user_id=pdf_file.user_id,
                    file_id=file_id,
                    old_status=old_status.value,
                    new_status=data.status.value,
                )
            )

        return pdf_file

    async def update_conversion_status(
        self,
        file_id: str,
        status: FileStatus,
        output_path: Optional[str] = None,
        conversion_result: Optional[str] = None,
        conversion_cost: int = 0,
    ) -> Optional[PDFFile]:
        """변환 상태 업데이트

        Args:
            file_id: 파일 ID
            status: 변환 상태
            output_path: 변환 결과 경로
            conversion_result: 변환 결과 메타데이터
            conversion_cost: 사용 포인트

        Returns:
            업데이트된 PDFFile
        """
        pdf_file = await self.get_pdf_file(file_id)
        if not pdf_file:
            return None

        old_status = pdf_file.status
        pdf_file.status = status
        pdf_file.output_path = output_path
        pdf_file.conversion_result = conversion_result
        pdf_file.conversion_cost = conversion_cost

        if status == FileStatus.PROCESSED:
            pdf_file.processed_at = datetime.utcnow()

        pdf_file.updated_at = datetime.utcnow()
        await self.db.flush()

        logger.info(
            f"✅ PDF 변환 상태 업데이트: {file_id} "
            f"{old_status.value} → {status.value}"
        )

        # 이벤트 발행
        if self.event_bus:
            from app.core.events import PDFConversionCompletedEvent
            if status == FileStatus.PROCESSED:
                await self.event_bus.emit(
                    PDFConversionCompletedEvent(
                        user_id=pdf_file.user_id,
                        file_id=file_id,
                        output_path=output_path,
                        conversion_cost=conversion_cost,
                    )
                )

        return pdf_file

    async def soft_delete_pdf_file(self, file_id: str) -> bool:
        """파일 소프트 삭제

        Args:
            file_id: 파일 ID

        Returns:
            성공 여부
        """
        pdf_file = await self.get_pdf_file(file_id)
        if not pdf_file:
            return False

        pdf_file.is_deleted = True
        pdf_file.status = FileStatus.DELETED
        pdf_file.updated_at = datetime.utcnow()
        await self.db.flush()

        logger.info(f"✅ PDF 파일 삭제: {file_id}")

        # 이벤트 발행
        if self.event_bus:
            from app.core.events import PDFFileDeletedEvent
            await self.event_bus.emit(
                PDFFileDeletedEvent(
                    user_id=pdf_file.user_id,
                    file_id=file_id,
                )
            )

        return True

    async def get_total_conversion_cost(self, user_id: int) -> int:
        """사용자의 총 변환 포인트 사용량

        Args:
            user_id: 사용자 ID

        Returns:
            총 사용 포인트
        """
        result = await self.db.execute(
            select(PDFFile).where(
                and_(
                    PDFFile.user_id == user_id,
                    PDFFile.is_deleted == False,
                )
            )
        )
        files = result.scalars().all()
        return sum(f.conversion_cost for f in files)
