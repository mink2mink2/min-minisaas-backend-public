"""JWT 재사용 방지 및 무효화 관리"""
from typing import Optional
from app.core.cache import cache


class JWTManager:
    """JWT 재사용 방지 및 토큰 무효화"""

    # Redis 키 프리픽스
    JWT_USED_PREFIX = "jwt_used"  # jwt_used:{user_id}:{iat}
    JWT_REVOKED_PREFIX = "jwt_revoked"  # jwt_revoked:{user_id}

    async def check_and_mark_used(self, user_id: str, iat: int, exp: int) -> bool:
        """
        JWT 사용 여부 확인 및 마크

        Args:
            user_id: 사용자 ID
            iat: JWT issued_at (발급 시간)
            exp: JWT expiration time (만료 시간)

        Returns:
            True if JWT is new, False if already used

        Raises:
            Exception: 검증 실패 시
        """
        key = f"{self.JWT_USED_PREFIX}:{user_id}:{iat}"
        existing = await cache.get(key)

        if existing:
            return False  # 이미 사용된 토큰

        # 토큰 남은 수명만큼 TTL 설정 (초 단위)
        ttl = max(exp - iat, 1)
        await cache.set(key, "used", ttl_seconds=ttl)

        return True

    async def revoke_user_jwts(self, user_id: str) -> None:
        """
        사용자의 모든 JWT 무효화

        Args:
            user_id: 사용자 ID
        """
        key = f"{self.JWT_REVOKED_PREFIX}:{user_id}"
        await cache.set(key, "revoked", ttl_seconds=86400 * 7)  # 7일

    async def is_revoked(self, user_id: str) -> bool:
        """
        사용자의 JWT가 무효화되었는지 확인

        Args:
            user_id: 사용자 ID

        Returns:
            True if revoked, False otherwise
        """
        key = f"{self.JWT_REVOKED_PREFIX}:{user_id}"
        return await cache.get(key) is not None


jwt_manager = JWTManager()
