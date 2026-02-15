"""PDF File Model - Integrated from pdf-helper-bapi

Migration Mapping:
  uploaded_files -> pdf_files (다른 프로젝트와 혼동 방지)
"""
import enum
from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, Enum as SAEnum, TIMESTAMP, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PGSUUID
from app.models.base import BaseModel


class FileStatus(enum.Enum):
    """파일 처리 상태"""
    UPLOADING = "uploading"      # 업로드 중
    UPLOADED = "uploaded"        # 업로드 완료
    PROCESSING = "processing"    # 변환 처리 중
    PROCESSED = "processed"      # 변환 완료
    FAILED = "failed"            # 변환 실패
    DELETED = "deleted"          # 삭제됨 (soft delete)


class FileType(enum.Enum):
    """파일 타입"""
    PDF = "pdf"
    IMAGE = "image"
    DOCUMENT = "document"


class PDFFile(BaseModel):
    """PDF 파일 정보

    Features:
    - UUID 기반 파일 추적
    - MinIO 저장소 경로 관리
    - 변환 상태 추적
    - 포인트 시스템 통합 (conversion_cost)
    """
    __tablename__ = "pdf_files"

    __table_args__ = (
        Index("ix_pdf_files_user_id", "user_id"),
        Index("ix_pdf_files_file_id", "file_id", unique=True),
        Index("ix_pdf_files_status", "status"),
        Index("ix_pdf_files_created_at", "created_at"),
    )

    # Primary Key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        comment="파일 레코드 ID",
    )

    # 식별자
    file_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="고유 파일 ID (UUID)",
    )

    # Foreign Keys
    user_id: Mapped[UUID] = mapped_column(
        PGSUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="파일 소유자 ID",
    )

    # 파일 정보
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="원본 파일명",
    )

    file_type: Mapped[FileType] = mapped_column(
        SAEnum(FileType),
        default=FileType.PDF,
        nullable=False,
        comment="파일 타입",
    )

    status: Mapped[FileStatus] = mapped_column(
        SAEnum(FileStatus),
        default=FileStatus.UPLOADING,
        nullable=False,
        comment="파일 상태",
    )

    # MinIO 저장소 정보
    minio_bucket: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="MinIO 버킷명",
    )

    minio_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="MinIO 경로",
    )

    # 파일 메타데이터
    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="파일 크기 (바이트)",
    )

    page_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="PDF 페이지 수",
    )

    # 변환 결과
    output_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="변환 결과 경로 (MinIO)",
    )

    conversion_result: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="변환 결과 (JSON 메타데이터)",
    )

    # 포인트 시스템
    conversion_cost: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="변환 사용 포인트",
    )

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="생성 시간",
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="수정 시간",
    )

    processed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="처리 완료 시간",
    )

    # 소프트 삭제
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="삭제 여부",
    )

    def __repr__(self):
        return f"<PDFFile(file_id={self.file_id}, user_id={self.user_id}, status={self.status})>"
