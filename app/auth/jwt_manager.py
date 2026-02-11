"""JWT 재사용 방지 및 무효화 관리"""
from typing import Optional
import hashlib
import json
from app.core.cache import cache


class JWTManager:
    """JWT 재사용 방지 및 토큰 무효화"""

    # Redis 키 프리픽스
    JWT_USED_PREFIX = "jwt_used"  # jwt_used:{user_id}:{iat}
    JWT_REVOKED_PREFIX = "jwt_revoked"  # jwt_revoked:{user_id}
    REFRESH_TOKEN_HISTORY_PREFIX = "refresh_token_history"  # refresh_token_history:{user_id}:{device_id}

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

    def _hash_token(self, token: str) -> str:
        """토큰을 해시 처리 (Redis에 저장할 때)"""
        return hashlib.sha256(token.encode()).hexdigest()

    async def detect_and_log_refresh_reuse(
        self,
        user_id: str,
        device_id: str,
        old_refresh_token: str,
        settings_refresh_expire_days: int,
    ) -> bool:
        """
        Refresh Token 재사용 탐지 및 기록

        Desktop 플랫폼에서 Refresh Token Rotation 공격 탐지:
        - 같은 refresh_token이 여러 번 사용되는 경우
        - 동시에 여러 새 토큰이 발급되는 경우

        Args:
            user_id: 사용자 ID
            device_id: 기기 ID
            old_refresh_token: 사용 중인 refresh_token
            settings_refresh_expire_days: 리프레시 토큰 만료 일수 (TTL 계산용)

        Returns:
            True if no reuse detected (정상)
            False if reuse detected (공격)

        Raises:
            Exception: SecurityLog 저장 실패 시
        """
        history_key = f"{self.REFRESH_TOKEN_HISTORY_PREFIX}:{user_id}:{device_id}"
        token_hash = self._hash_token(old_refresh_token)

        # 기존 히스토리 조회
        history_data = await cache.get(history_key)
        if history_data is None:
            history_data = {
                "tokens": {},
                "generation_count": 0,
            }

        # 토큰이 이미 사용되었는지 확인
        if token_hash in history_data["tokens"]:
            # 🔴 토큰 재사용 감지!
            # SecurityLog 기록
            await self._log_security_event(
                user_id=user_id,
                event_type="TOKEN_REUSE_DETECTED",
                device_id=device_id,
                details={
                    "token_hash": token_hash,
                    "generation_count": history_data["generation_count"],
                    "previous_usage": history_data["tokens"].get(token_hash),
                },
            )
            return False

        # 정상 토큰 사용: 히스토리에 기록
        import time

        history_data["tokens"][token_hash] = int(time.time())
        history_data["generation_count"] += 1

        # Redis에 업데이트 (TTL = REFRESH_TOKEN_EXPIRE_DAYS)
        ttl = settings_refresh_expire_days * 86400
        await cache.set(history_key, history_data, ttl_seconds=ttl)

        return True

    async def _log_security_event(
        self,
        user_id: str,
        event_type: str,
        device_id: str = None,
        details: dict = None,
    ) -> None:
        """
        보안 이벤트를 SecurityLog 데이터베이스에 기록

        Args:
            user_id: 사용자 ID
            event_type: 이벤트 타입 (TOKEN_REUSE_DETECTED 등)
            device_id: 기기 ID (선택)
            details: 추가 정보 (선택)
        """
        from app.core.database import AsyncSessionLocal
        from app.models.security_log import SecurityLog

        try:
            async with AsyncSessionLocal() as db:
                log = SecurityLog(
                    user_id=user_id,
                    event_type=event_type,
                    device_id=device_id,
                    details=details or {},
                )
                db.add(log)
                await db.commit()
        except Exception as e:
            # 로깅 실패해도 인증 흐름을 중단하지 않음
            print(f"Failed to log security event: {str(e)}")


jwt_manager = JWTManager()
