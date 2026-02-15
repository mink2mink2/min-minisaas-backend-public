"""PDF File Schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.domain.pdf.models import FileStatus, FileType


class PDFFileCreate(BaseModel):
    """PDF 파일 생성 요청"""
    original_filename: str = Field(..., min_length=1, max_length=255)
    file_size_bytes: int = Field(..., gt=0)
    file_type: FileType = Field(default=FileType.PDF)


class PDFFileUpdate(BaseModel):
    """PDF 파일 수정 요청"""
    status: Optional[FileStatus] = None
    page_count: Optional[int] = None
    output_path: Optional[str] = None
    conversion_result: Optional[str] = None
    conversion_cost: Optional[int] = None
    processed_at: Optional[datetime] = None


class PDFFileResponse(BaseModel):
    """PDF 파일 응답"""
    file_id: str
    user_id: str  # UUID
    original_filename: str
    file_type: str  # FileType enum 값
    status: str  # FileStatus enum 값
    minio_path: str
    file_size_bytes: int
    page_count: Optional[int] = None
    output_path: Optional[str] = None
    conversion_cost: int = 0
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    is_deleted: bool = False

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        """ORM 객체에서 변환"""
        return cls(
            file_id=obj.file_id,
            user_id=str(obj.user_id),
            original_filename=obj.original_filename,
            file_type=obj.file_type.value if hasattr(obj.file_type, 'value') else str(obj.file_type),
            status=obj.status.value if hasattr(obj.status, 'value') else str(obj.status),
            minio_path=obj.minio_path,
            file_size_bytes=obj.file_size_bytes,
            page_count=obj.page_count,
            output_path=obj.output_path,
            conversion_cost=obj.conversion_cost,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            processed_at=obj.processed_at,
            is_deleted=obj.is_deleted,
        )


class PDFConversionRequest(BaseModel):
    """PDF 변환 요청"""
    file_id: str = Field(..., description="변환할 파일 ID")
    conversion_type: str = Field(
        default="table_to_csv",
        description="변환 타입 (table_to_csv, extract_text, ...)"
    )
    options: Optional[dict] = Field(
        default=None,
        description="변환 옵션"
    )


class PDFConversionResponse(BaseModel):
    """PDF 변환 응답"""
    file_id: str
    status: FileStatus
    conversion_cost: int
    output_path: Optional[str] = None
    message: str
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
