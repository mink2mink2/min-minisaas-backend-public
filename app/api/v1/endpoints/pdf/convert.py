"""PDF 변환 엔드포인트"""
import logging
import asyncio
from typing import Optional
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.dependencies.auth import verify_any_platform
from app.domain.auth.models import User
from app.domain.pdf.models import FileStatus
from app.domain.pdf.schemas import PDFConversionRequest, PDFConversionResponse
from app.domain.pdf.services import PDFFileService, PDFConverterService
from app.domain.points.services.point_service import PointService, InsufficientPointsError
from app.infrastructure.minio_client import MinIOClient, MinIOClientError
from app.core.events import event_bus
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["pdf"])

CONVERSION_COST = 10  # 포인트

# MinIO 클라이언트
minio = None
try:
    minio = MinIOClient()
except Exception as e:
    logger.warning(f"⚠️ MinIO 초기화 실패: {e}")


async def convert_pdf_background(
    file_id: str,
    db: AsyncSession,
):
    """백그라운드에서 PDF 변환 처리

    Args:
        file_id: 파일 ID
        db: 데이터베이스 세션
    """
    pdf_service = PDFFileService(db, event_bus)
    converter_service = PDFConverterService(event_bus)

    try:
        # 파일 정보 조회
        pdf_file = await pdf_service.get_pdf_file(file_id)
        if not pdf_file:
            logger.error(f"❌ 파일을 찾을 수 없음: {file_id}")
            return

        logger.info(f"🔄 PDF 변환 시작: {file_id}")

        # 상태 업데이트: PROCESSING
        await pdf_service.update_conversion_status(
            file_id=file_id,
            status=FileStatus.PROCESSING,
        )
        await db.commit()

        # MinIO에서 다운로드
        if not minio:
            logger.error("❌ MinIO 클라이언트를 사용할 수 없음")
            raise Exception("MinIO 클라이언트를 사용할 수 없음")

        try:
            file_data = await minio.download_file(
                bucket_name=pdf_file.minio_bucket,
                object_name=pdf_file.minio_path,
            )
        except MinIOClientError as e:
            logger.error(f"❌ MinIO 다운로드 실패: {e}")
            await pdf_service.update_conversion_status(
                file_id=file_id,
                status=FileStatus.FAILED,
            )
            await db.commit()
            return

        # 임시 파일에 저장
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_in:
            tmp_in.write(file_data.getvalue())
            tmp_in.flush()
            input_path = tmp_in.name

        # 임시 출력 파일
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_out:
            output_path = tmp_out.name

        # PDF 변환
        result = await converter_service.convert_pdf_to_csv(
            input_path=input_path,
            output_path=output_path,
        )

        # 임시 입력 파일 삭제
        Path(input_path).unlink(missing_ok=True)

        if not result.get("success"):
            logger.error(f"❌ 변환 실패: {result.get('error')}")
            await pdf_service.update_conversion_status(
                file_id=file_id,
                status=FileStatus.FAILED,
            )
            await db.commit()
            Path(output_path).unlink(missing_ok=True)
            return

        # 변환 결과를 MinIO에 업로드
        output_file_size = Path(output_path).stat().st_size
        output_minio_path = pdf_file.minio_path.rsplit("/", 1)[0] + "/output.csv"

        try:
            with open(output_path, "rb") as f:
                await minio.upload_file(
                    bucket_name=pdf_file.minio_bucket,
                    object_name=output_minio_path,
                    file_data=f,
                    file_size=output_file_size,
                    content_type="text/csv",
                )
        except MinIOClientError as e:
            logger.error(f"❌ 변환 결과 업로드 실패: {e}")
            await pdf_service.update_conversion_status(
                file_id=file_id,
                status=FileStatus.FAILED,
            )
            await db.commit()
            Path(output_path).unlink(missing_ok=True)
            return

        # 임시 출력 파일 삭제
        Path(output_path).unlink(missing_ok=True)

        # 포인트 차감 (변환 완료 후)
        conversion_cost = CONVERSION_COST
        try:
            point_service = PointService(db)
            await point_service.consume(
                user_id=pdf_file.user_id,
                amount=conversion_cost,
                description=f"PDF 변환: {pdf_file.original_filename}",
                idempotency_key=f"pdf_convert_{file_id}",
            )
        except InsufficientPointsError:
            logger.error(f"❌ 포인트 부족으로 차감 실패: {file_id}")
            # 변환 성공했지만 포인트 차감 실패 - 상태는 PROCESSED로 업데이트하되, conversion_cost=0으로 설정
            conversion_cost = 0
        except Exception as e:
            logger.error(f"❌ 포인트 차감 중 오류: {e}")
            # 포인트 차감 실패해도 변환 결과는 유지
            conversion_cost = 0

        # 상태 업데이트: PROCESSED + 결과 저장
        await pdf_service.update_conversion_status(
            file_id=file_id,
            status=FileStatus.PROCESSED,
            output_path=output_minio_path,
            conversion_result=str(result),
            conversion_cost=conversion_cost,
        )
        await db.commit()

        logger.info(
            f"✅ PDF 변환 완료: {file_id} "
            f"({result.get('table_count')} 테이블, "
            f"{result.get('rows')} 행)"
        )

    except Exception as e:
        logger.error(f"❌ 변환 중 오류: {e}")
        try:
            await pdf_service.update_conversion_status(
                file_id=file_id,
                status=FileStatus.FAILED,
            )
            await db.commit()
        except Exception as db_err:
            logger.error(f"❌ DB 업데이트 실패: {db_err}")


@router.post("/{file_id}/convert", response_model=PDFConversionResponse)
async def request_pdf_conversion(
    file_id: str,
    request: Optional[PDFConversionRequest] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(verify_any_platform),
):
    """PDF 변환 요청 (비동기)

    - 요청을 받으면 즉시 응답
    - 백그라운드에서 변환 처리
    - 상태는 /status 엔드포인트로 조회

    Args:
        file_id: 파일 ID
        request: 변환 요청 (선택사항)
        background_tasks: FastAPI 백그라운드 작업
        db: 데이터베이스 세션
        current_user: 인증된 사용자

    Returns:
        PDFConversionResponse

    Raises:
        404: 파일을 찾을 수 없음
        403: 접근 권한 없음
        409: 이미 변환 중이거나 완료됨
    """
    pdf_service = PDFFileService(db)
    pdf_file = await pdf_service.get_pdf_file(file_id)

    if not pdf_file:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    # 권한 확인
    if str(pdf_file.user_id) != str(current_user.user_id):
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

    # 상태 확인
    if pdf_file.status == FileStatus.PROCESSING:
        raise HTTPException(
            status_code=409,
            detail="이미 변환 중입니다.",
        )

    if pdf_file.status == FileStatus.PROCESSED:
        raise HTTPException(
            status_code=409,
            detail="이미 변환이 완료되었습니다.",
        )

    # 포인트 잔액 확인
    point_service = PointService(db)
    balance = await point_service.get_balance(current_user.user_id)
    if balance < CONVERSION_COST:
        raise HTTPException(
            status_code=402,
            detail=f"포인트가 부족합니다. 필요: {CONVERSION_COST}, 잔액: {balance}",
        )

    # 백그라운드 작업 추가
    background_tasks.add_task(convert_pdf_background, file_id, db)

    logger.info(f"📤 PDF 변환 요청: {file_id}")

    return PDFConversionResponse(
        file_id=file_id,
        status=FileStatus.PROCESSING,
        conversion_cost=0,  # 완료 후 차감
        message="변환이 시작되었습니다. 잠시 후 상태를 확인해주세요.",
        created_at=pdf_file.created_at,
        processed_at=None,
    )


@router.get("/{file_id}/status", response_model=PDFConversionResponse)
async def get_conversion_status(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(verify_any_platform),
):
    """PDF 변환 상태 조회

    Args:
        file_id: 파일 ID
        db: 데이터베이스 세션
        current_user: 인증된 사용자

    Returns:
        PDFConversionResponse

    Raises:
        404: 파일을 찾을 수 없음
        403: 접근 권한 없음
    """
    pdf_service = PDFFileService(db)
    pdf_file = await pdf_service.get_pdf_file(file_id)

    if not pdf_file:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    if str(pdf_file.user_id) != str(current_user.user_id):
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

    # 상태 메시지
    status_messages = {
        FileStatus.UPLOADING: "파일 업로드 중입니다.",
        FileStatus.UPLOADED: "파일이 준비되었습니다. 변환을 요청해주세요.",
        FileStatus.PROCESSING: "변환 중입니다. 잠시만 기다려주세요.",
        FileStatus.PROCESSED: "변환이 완료되었습니다.",
        FileStatus.FAILED: "변환에 실패했습니다.",
        FileStatus.DELETED: "파일이 삭제되었습니다.",
    }

    return PDFConversionResponse(
        file_id=file_id,
        status=pdf_file.status,
        conversion_cost=pdf_file.conversion_cost,
        output_path=pdf_file.output_path,
        message=status_messages.get(
            pdf_file.status, "상태를 확인할 수 없습니다."
        ),
        created_at=pdf_file.created_at,
        processed_at=pdf_file.processed_at,
    )


@router.get("/{file_id}/download")
async def download_converted_csv(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(verify_any_platform),
):
    """변환된 CSV 파일 다운로드 (스트리밍)

    Args:
        file_id: 파일 ID
        db: 데이터베이스 세션
        current_user: 인증된 사용자

    Returns:
        StreamingResponse (CSV 파일)

    Raises:
        404: 파일을 찾을 수 없음
        403: 접근 권한 없음
        409: 변환이 완료되지 않음
        503: MinIO 저장소 사용 불가
    """
    pdf_service = PDFFileService(db)
    pdf_file = await pdf_service.get_pdf_file(file_id)

    if not pdf_file:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    # 권한 확인
    if str(pdf_file.user_id) != str(current_user.user_id):
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

    # 상태 확인
    if pdf_file.status != FileStatus.PROCESSED or not pdf_file.output_path:
        raise HTTPException(
            status_code=409,
            detail="변환이 완료되지 않았습니다.",
        )

    # MinIO에서 다운로드
    if not minio:
        raise HTTPException(
            status_code=503,
            detail="파일 저장소를 사용할 수 없습니다.",
        )

    try:
        file_data = await minio.download_file(
            bucket_name=pdf_file.minio_bucket,
            object_name=pdf_file.output_path,
        )
    except MinIOClientError as e:
        logger.error(f"❌ MinIO 다운로드 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail="파일 다운로드에 실패했습니다.",
        )

    # 파일명 설정 (원본 파일명에서 확장자를 .csv로 변경)
    filename = pdf_file.original_filename.rsplit(".", 1)[0] + ".csv"
    encoded_filename = quote(filename)

    logger.info(f"📥 CSV 다운로드: {file_id} -> {filename}")

    return StreamingResponse(
        file_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        },
    )
