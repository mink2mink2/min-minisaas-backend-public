"""PDF Domain - File Management & Conversion

Architecture:
- Models: PDFFile (파일 메타데이터)
- Services: PDFConverterService (변환 로직), PDFFileService (CRUD)
- Schemas: 요청/응답 스키마
- Events: 이벤트 드리븐 통합

Integration Points:
- Points System: conversion_cost 추적
- Event Bus: 파일 및 변환 이벤트
- MinIO Storage: 파일 저장소
"""
from app.domain.pdf.models import PDFFile, FileStatus, FileType
from app.domain.pdf.schemas import (
    PDFFileCreate,
    PDFFileUpdate,
    PDFFileResponse,
    PDFConversionRequest,
    PDFConversionResponse,
)
from app.domain.pdf.services import PDFConverterService, PDFFileService

__all__ = [
    # Models
    "PDFFile",
    "FileStatus",
    "FileType",
    # Schemas
    "PDFFileCreate",
    "PDFFileUpdate",
    "PDFFileResponse",
    "PDFConversionRequest",
    "PDFConversionResponse",
    # Services
    "PDFConverterService",
    "PDFFileService",
]
