"""MinIO 저장소 클라이언트

Features:
- 파일 업로드/다운로드
- 버킷 관리 (자동 생성)
- 공개/비공개 제어
- 에러 처리
"""
import logging
import io
from typing import Optional, BinaryIO
from minio import Minio
from minio.error import S3Error
from app.core.config import settings

logger = logging.getLogger(__name__)


class MinIOClientError(Exception):
    """MinIO 클라이언트 에러"""
    pass


class MinIOClient:
    """MinIO 클라이언트 래퍼

    책임:
    - 파일 업로드/다운로드
    - 버킷 관리
    - 에러 처리
    """

    def __init__(self):
        """MinIO 클라이언트 초기화"""
        try:
            self.client = Minio(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
            logger.info("✅ MinIO 클라이언트 초기화 성공")
        except Exception as e:
            logger.error(f"❌ MinIO 클라이언트 초기화 실패: {e}")
            raise MinIOClientError(f"MinIO 초기화 실패: {e}")

    async def ensure_bucket(self, bucket_name: str) -> bool:
        """버킷 존재 확인, 없으면 생성

        Args:
            bucket_name: 버킷명

        Returns:
            성공 여부

        Raises:
            MinIOClientError: 버킷 생성 실패
        """
        try:
            exists = self.client.bucket_exists(bucket_name)
            if not exists:
                self.client.make_bucket(bucket_name)
                logger.info(f"✅ MinIO 버킷 생성: {bucket_name}")
            return True
        except S3Error as e:
            logger.error(f"❌ 버킷 관리 실패: {e}")
            raise MinIOClientError(f"버킷 관리 실패: {e}")

    async def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        file_data: BinaryIO,
        file_size: int,
        content_type: str = "application/octet-stream",
    ) -> str:
        """파일 업로드

        Args:
            bucket_name: 버킷명
            object_name: 객체명 (경로)
            file_data: 파일 데이터 (바이너리)
            file_size: 파일 크기 (바이트)
            content_type: MIME 타입

        Returns:
            업로드된 객체명

        Raises:
            MinIOClientError: 업로드 실패
        """
        try:
            # 버킷 확인
            await self.ensure_bucket(bucket_name)

            # 파일 업로드
            self.client.put_object(
                bucket_name,
                object_name,
                file_data,
                file_size,
                content_type=content_type,
            )

            logger.info(
                f"✅ 파일 업로드 성공: {bucket_name}/{object_name} "
                f"({file_size} bytes)"
            )

            return object_name

        except S3Error as e:
            logger.error(f"❌ 파일 업로드 실패: {e}")
            raise MinIOClientError(f"파일 업로드 실패: {e}")
        except Exception as e:
            logger.error(f"❌ 예기치 않은 오류: {e}")
            raise MinIOClientError(f"예기치 않은 오류: {e}")

    async def download_file(
        self,
        bucket_name: str,
        object_name: str,
    ) -> io.BytesIO:
        """파일 다운로드

        Args:
            bucket_name: 버킷명
            object_name: 객체명

        Returns:
            파일 데이터 (BytesIO)

        Raises:
            MinIOClientError: 다운로드 실패
        """
        try:
            response = self.client.get_object(bucket_name, object_name)
            data = io.BytesIO(response.read())
            response.close()
            response.release_conn()

            logger.info(
                f"✅ 파일 다운로드 성공: {bucket_name}/{object_name}"
            )

            return data

        except S3Error as e:
            logger.error(f"❌ 파일 다운로드 실패: {e}")
            raise MinIOClientError(f"파일 다운로드 실패: {e}")

    async def file_exists(
        self,
        bucket_name: str,
        object_name: str,
    ) -> bool:
        """파일 존재 확인

        Args:
            bucket_name: 버킷명
            object_name: 객체명

        Returns:
            존재 여부
        """
        try:
            self.client.stat_object(bucket_name, object_name)
            return True
        except S3Error:
            return False

    async def delete_file(
        self,
        bucket_name: str,
        object_name: str,
    ) -> bool:
        """파일 삭제

        Args:
            bucket_name: 버킷명
            object_name: 객체명

        Returns:
            성공 여부

        Raises:
            MinIOClientError: 삭제 실패
        """
        try:
            self.client.remove_object(bucket_name, object_name)
            logger.info(
                f"✅ 파일 삭제 성공: {bucket_name}/{object_name}"
            )
            return True
        except S3Error as e:
            logger.error(f"❌ 파일 삭제 실패: {e}")
            raise MinIOClientError(f"파일 삭제 실패: {e}")

    async def get_presigned_url(
        self,
        bucket_name: str,
        object_name: str,
        expiration: int = 3600,
    ) -> str:
        """서명된 다운로드 URL 생성 (임시)

        Args:
            bucket_name: 버킷명
            object_name: 객체명
            expiration: 만료 시간 (초, 기본 1시간)

        Returns:
            임시 다운로드 URL

        Raises:
            MinIOClientError: URL 생성 실패
        """
        try:
            url = self.client.get_presigned_download_url(
                bucket_name,
                object_name,
                expires=expiration,
            )
            logger.info(
                f"✅ 서명된 URL 생성: {bucket_name}/{object_name}"
            )
            return url
        except S3Error as e:
            logger.error(f"❌ URL 생성 실패: {e}")
            raise MinIOClientError(f"URL 생성 실패: {e}")
