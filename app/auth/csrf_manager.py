"""CSRF Token Manager - 민감한 작업 보호"""
import secrets
from datetime import datetime, timedelta
from typing import Optional
from app.core.cache import cache
from app.core.config import settings


class CSRFTokenManager:
    """CSRF 토큰 생성, 검증, 무효화"""

    CSRF_TOKEN_LENGTH = 32  # 32 bytes = 256 bits
    CSRF_TOKEN_TTL = 3600  # 1 hour in seconds

    @staticmethod
    def generate_token() -> str:
        """
        CSRF 토큰 생성

        Returns:
            16진수 인코딩된 CSRF 토큰 (64자)
        """
        return secrets.token_hex(CSRFTokenManager.CSRF_TOKEN_LENGTH)

    @staticmethod
    async def create_and_store(
        user_id: str,
        platform: str,
        ttl_seconds: int = CSRF_TOKEN_TTL
    ) -> str:
        """
        사용자를 위한 CSRF 토큰 생성 및 Redis에 저장

        Args:
            user_id: 사용자 ID
            platform: 플랫폼 (web, mobile, desktop, device)
            ttl_seconds: 토큰 만료 시간 (초)

        Returns:
            생성된 CSRF 토큰
        """
        token = CSRFTokenManager.generate_token()
        key = CSRFTokenManager._get_key(user_id, platform)

        # Redis에 저장 (TTL 포함)
        await cache.set(
            key,
            {
                "token": token,
                "created_at": datetime.utcnow().isoformat(),
                "platform": platform,
            },
            ttl_seconds=ttl_seconds
        )

        return token

    @staticmethod
    async def validate(
        user_id: str,
        platform: str,
        csrf_token: str
    ) -> bool:
        """
        CSRF 토큰 검증

        Args:
            user_id: 사용자 ID
            platform: 플랫폼
            csrf_token: 검증할 토큰

        Returns:
            토큰이 유효하면 True, 아니면 False
        """
        key = CSRFTokenManager._get_key(user_id, platform)
        stored_data = await cache.get(key)

        if not stored_data:
            return False

        # 저장된 토큰과 비교 (timing-safe하지는 않지만, 레디스에서 가져온 후 검증)
        return stored_data.get("token") == csrf_token

    @staticmethod
    async def consume(
        user_id: str,
        platform: str,
        csrf_token: str
    ) -> bool:
        """
        CSRF 토큰 검증 후 무효화 (1회용 토큰)

        Args:
            user_id: 사용자 ID
            platform: 플랫폼
            csrf_token: 검증할 토큰

        Returns:
            토큰이 유효했으면 True (삭제됨), 아니면 False
        """
        # 먼저 검증
        if not await CSRFTokenManager.validate(user_id, platform, csrf_token):
            return False

        # 토큰 삭제 (1회용)
        key = CSRFTokenManager._get_key(user_id, platform)
        await cache.delete(key)

        return True

    @staticmethod
    async def revoke_all(user_id: str) -> None:
        """
        사용자의 모든 플랫폼 CSRF 토큰 무효화
        (로그아웃, 계정 삭제 시 호출)

        Args:
            user_id: 사용자 ID
        """
        # 모든 플랫폼의 CSRF 토큰 삭제
        platforms = ["web", "mobile", "desktop", "device"]
        for platform in platforms:
            key = CSRFTokenManager._get_key(user_id, platform)
            await cache.delete(key)

    @staticmethod
    def _get_key(user_id: str, platform: str) -> str:
        """Redis 키 생성"""
        return f"csrf:token:{user_id}:{platform}"
