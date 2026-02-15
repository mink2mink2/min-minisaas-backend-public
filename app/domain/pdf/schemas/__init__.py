"""PDF Domain Schemas"""
from app.domain.pdf.schemas.pdf_file import (
    PDFFileCreate,
    PDFFileUpdate,
    PDFFileResponse,
    PDFConversionRequest,
    PDFConversionResponse,
)

__all__ = [
    "PDFFileCreate",
    "PDFFileUpdate",
    "PDFFileResponse",
    "PDFConversionRequest",
    "PDFConversionResponse",
]
