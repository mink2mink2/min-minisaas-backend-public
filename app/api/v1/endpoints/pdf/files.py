"""PDF 파일 관리 엔드포인트 (업로드, 조회, 삭제)"""
import logging
import uuid
from typing import List
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.dependencies.auth import verify_any_platform
from app.domain.auth.models import User
from app.domain.pdf.schemas import PDFFileCreate, PDFFileResponse
from app.domain.pdf.services import PDFFileService
from app.infrastructure.minio_client import MinIOClient, MinIOClientError
from app.core.config import settings
from app.core.events import event_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["pdf"])

# MinIO 클라이언트
minio = None
try:
    minio = MinIOClient()
except Exception as e:
    logger.warning(f"⚠️ MinIO 초기화 실패: {e}")


class FileTooLargeError(Exception):
    """파일 너무 큼"""
    pass


# 최대 파일 크기 (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024


@router.post("/upload", response_model=PDFFileResponse, status_code=201)
async def upload_pdf(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(verify_any_platform),
):
    """PDF 파일 업로드

    - 파일: PDF 형식만 허용
    - 최대 크기: 100MB
    - MinIO에 저장
    - 메타데이터를 DB에 저장

    Args:
        file: 업로드 파일
        db: 데이터베이스 세션
        current_user: 인증된 사용자

    Returns:
        생성된 PDFFileResponse

    Raises:
        400: 파일 형식 오류 또는 크기 초과
        500: MinIO 저장 실패
    """
    try:
        # 파일 검증
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

        if file.content_type not in ["application/pdf"]:
            raise HTTPException(
                status_code=400,
                detail="지원되지 않는 파일 형식입니다. (application/pdf)",
            )

        # 파일 크기 확인
        content = await file.read()
        file_size = len(content)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"파일이 너무 큽니다. 최대 크기: 100MB",
            )

        if file_size == 0:
            raise HTTPException(status_code=400, detail="빈 파일입니다.")

        logger.info(
            f"📤 파일 업로드 시작: {file.filename} ({file_size} bytes) "
            f"- User: {current_user.id}"
        )

        # MinIO에 저장
        if not minio:
            raise HTTPException(
                status_code=503,
                detail="파일 저장소를 사용할 수 없습니다.",
            )

        # MinIO 경로 생성
        minio_bucket = "pdf-files"
        file_id = str(uuid.uuid4())
        minio_path = f"{current_user.id}/{file_id}/{file.filename}"

        try:
            await minio.ensure_bucket(minio_bucket)
            await minio.upload_file(
                bucket_name=minio_bucket,
                object_name=minio_path,
                file_data=file.file,
                file_size=file_size,
                content_type="application/pdf",
            )
        except MinIOClientError as e:
            logger.error(f"❌ MinIO 저장 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail="파일 저장에 실패했습니다.",
            )

        # DB에 저장
        pdf_service = PDFFileService(db, event_bus)

        pdf_file_data = PDFFileCreate(
            original_filename=file.filename,
            file_size_bytes=file_size,
        )

        pdf_file = await pdf_service.create_pdf_file(
            user_id=current_user.id,
            data=pdf_file_data,
            minio_bucket=minio_bucket,
            minio_path=minio_path,
        )

        await db.commit()

        logger.info(f"✅ 파일 업로드 완료: {file_id}")

        return PDFFileResponse.from_orm(pdf_file)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 파일 업로드 중 오류: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="파일 업로드에 실패했습니다.")


@router.get("/{file_id}", response_model=PDFFileResponse)
async def get_pdf_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(verify_any_platform),
):
    """PDF 파일 정보 조회

    Args:
        file_id: 파일 ID
        db: 데이터베이스 세션
        current_user: 인증된 사용자

    Returns:
        PDFFileResponse

    Raises:
        404: 파일을 찾을 수 없음
        403: 접근 권한 없음
    """
    pdf_service = PDFFileService(db)
    pdf_file = await pdf_service.get_pdf_file(file_id)

    if not pdf_file:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    # 권한 확인 (본인 파일만)
    if pdf_file.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

    return PDFFileResponse.from_orm(pdf_file)


@router.get("/user/files", response_model=List[PDFFileResponse])
async def get_user_pdf_files(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(verify_any_platform),
):
    """사용자의 PDF 파일 목록 조회

    Args:
        skip: 건너뛸 개수
        limit: 조회할 개수
        db: 데이터베이스 세션
        current_user: 인증된 사용자

    Returns:
        PDFFileResponse 목록
    """
    pdf_service = PDFFileService(db)
    files = await pdf_service.get_user_pdf_files(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )

    return [PDFFileResponse.from_orm(f) for f in files]


@router.delete("/{file_id}", status_code=204)
async def delete_pdf_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(verify_any_platform),
):
    """PDF 파일 삭제 (소프트 삭제)

    Args:
        file_id: 파일 ID
        db: 데이터베이스 세션
        current_user: 인증된 사용자

    Raises:
        404: 파일을 찾을 수 없음
        403: 접근 권한 없음
    """
    pdf_service = PDFFileService(db, event_bus)
    pdf_file = await pdf_service.get_pdf_file(file_id)

    if not pdf_file:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    if pdf_file.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

    # MinIO에서도 삭제 시도 (실패해도 계속 진행)
    if minio:
        try:
            await minio.delete_file(pdf_file.minio_bucket, pdf_file.minio_path)
        except MinIOClientError as e:
            logger.warning(f"⚠️ MinIO 삭제 실패: {e}")

    # 소프트 삭제
    await pdf_service.soft_delete_pdf_file(file_id)
    await db.commit()

    logger.info(f"✅ 파일 삭제: {file_id}")
