"""PDF 변환 서비스 - pdf-helper-bapi에서 포팅

Features:
- 테이블 추출 (라인/텍스트 기반)
- CSV 변환
- 이벤트 드리븐 아키텍처
"""
import logging
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import pdfplumber
import pandas as pd
from app.core.events import EventBus

logger = logging.getLogger(__name__)


class PDFConverterError(Exception):
    """PDF 변환 에러"""
    pass


class PDFConverterService:
    """PDF 파일 변환 서비스

    책임:
    - PDF 테이블 추출 (라인/텍스트 기반)
    - CSV 변환
    - 메타데이터 추출 (페이지 수 등)
    - 이벤트 발행
    """

    # 테이블 추출 설정
    LINE_SETTINGS = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 3,
        "join_tolerance": 3,
    }

    TEXT_SETTINGS = {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "intersection_tolerance": 5,
    }

    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Args:
            event_bus: 이벤트 버스 (PDF 변환 이벤트 발행용)
        """
        self.event_bus = event_bus

    async def convert_pdf_to_csv(
        self,
        input_path: str,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """PDF 파일을 CSV로 변환

        Args:
            input_path: 입력 PDF 경로
            output_path: 출력 CSV 경로 (None이면 임시 경로 생성)

        Returns:
            변환 결과:
            {
                "success": bool,
                "page_count": int,
                "table_count": int,
                "output_path": str,
                "error": str (실패시)
            }

        Raises:
            PDFConverterError: 변환 실패
        """
        try:
            input_path_obj = Path(input_path)
            if not input_path_obj.exists():
                raise PDFConverterError(f"입력 파일 없음: {input_path}")

            # 출력 경로 생성
            if output_path is None:
                temp_file = tempfile.NamedTemporaryFile(
                    suffix=".csv", delete=False, mode="w"
                )
                output_path = temp_file.name
                temp_file.close()

            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)

            # PDF 처리
            tables_df = []
            page_count = 0

            try:
                with pdfplumber.open(input_path) as pdf:
                    page_count = len(pdf.pages)

                    for page_num, page in enumerate(pdf.pages, start=1):
                        try:
                            # 1) 라인 기반 추출
                            tables = page.extract_tables(
                                table_settings=self.LINE_SETTINGS
                            ) or []

                            # 2) 실패하면 텍스트 기반 추출
                            if not tables:
                                tables = page.extract_tables(
                                    table_settings=self.TEXT_SETTINGS
                                ) or []

                            for table in tables:
                                df = pd.DataFrame(table)
                                # 빈 행/열 제거
                                df = df.dropna(how="all").dropna(axis=1, how="all")
                                if not df.empty:
                                    tables_df.append(df)

                        except Exception as e:
                            logger.warning(
                                f"페이지 {page_num} 처리 실패: {e}"
                            )
                            continue

            except Exception as e:
                raise PDFConverterError(f"PDF 읽기 실패: {e}")

            if not tables_df:
                raise PDFConverterError("추출된 테이블 없음")

            # CSV 저장
            try:
                combined_df = pd.concat(tables_df, ignore_index=True)
                combined_df.to_csv(output_path, index=False, encoding="utf-8-sig")
            except Exception as e:
                raise PDFConverterError(f"CSV 저장 실패: {e}")

            result = {
                "success": True,
                "page_count": page_count,
                "table_count": len(tables_df),
                "output_path": str(output_path),
                "rows": len(combined_df),
                "columns": len(combined_df.columns),
            }

            logger.info(
                f"✅ PDF 변환 성공: {page_count}쪽, "
                f"{len(tables_df)}개 테이블, {len(combined_df)}행"
            )

            return result

        except PDFConverterError as e:
            logger.error(f"❌ PDF 변환 실패: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"❌ 예기치 않은 오류: {e}")
            return {
                "success": False,
                "error": f"예기치 않은 오류: {e}",
            }

    async def extract_text(self, input_path: str) -> Dict[str, Any]:
        """PDF에서 텍스트 추출

        Args:
            input_path: 입력 PDF 경로

        Returns:
            추출 결과:
            {
                "success": bool,
                "text": str,
                "page_count": int,
                "error": str (실패시)
            }
        """
        try:
            input_path_obj = Path(input_path)
            if not input_path_obj.exists():
                raise PDFConverterError(f"입력 파일 없음: {input_path}")

            text_content = []
            page_count = 0

            with pdfplumber.open(input_path) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)

            if not text_content:
                raise PDFConverterError("추출된 텍스트 없음")

            full_text = "\n---PAGE BREAK---\n".join(text_content)

            return {
                "success": True,
                "text": full_text,
                "page_count": page_count,
                "char_count": len(full_text),
            }

        except PDFConverterError as e:
            logger.error(f"❌ 텍스트 추출 실패: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"❌ 예기치 않은 오류: {e}")
            return {
                "success": False,
                "error": f"예기치 않은 오류: {e}",
            }

    async def get_metadata(self, input_path: str) -> Dict[str, Any]:
        """PDF 메타데이터 추출

        Args:
            input_path: 입력 PDF 경로

        Returns:
            메타데이터:
            {
                "success": bool,
                "page_count": int,
                "file_size_mb": float,
                "title": str,
                "author": str,
                ...
            }
        """
        try:
            input_path_obj = Path(input_path)
            if not input_path_obj.exists():
                raise PDFConverterError(f"입력 파일 없음: {input_path}")

            file_size_mb = input_path_obj.stat().st_size / (1024 * 1024)

            with pdfplumber.open(input_path) as pdf:
                metadata = pdf.metadata or {}
                page_count = len(pdf.pages)

            return {
                "success": True,
                "page_count": page_count,
                "file_size_mb": round(file_size_mb, 2),
                "title": metadata.get("Title", ""),
                "author": metadata.get("Author", ""),
                "subject": metadata.get("Subject", ""),
                "creator": metadata.get("Creator", ""),
            }

        except PDFConverterError as e:
            logger.error(f"❌ 메타데이터 추출 실패: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"❌ 예기치 않은 오류: {e}")
            return {
                "success": False,
                "error": f"예기치 않은 오류: {e}",
            }
