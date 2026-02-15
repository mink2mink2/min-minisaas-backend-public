"""PDF API 엔드포인트"""
from fastapi import APIRouter
from app.api.v1.endpoints.pdf.files import router as files_router
from app.api.v1.endpoints.pdf.convert import router as convert_router

pdf_router = APIRouter(prefix="/pdf", tags=["pdf"])

# 서브 라우터 등록
pdf_router.include_router(files_router)
pdf_router.include_router(convert_router)

__all__ = ["pdf_router"]
