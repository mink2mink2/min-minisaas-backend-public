"""서버사이드 세션 관리 (Redis)"""
import uuid
import time
from typing import Optional, Dict, Any
from app.core.cache import cache
from app.core.config import settings


class SessionManager:
    """Redis 기반 서버사이드 세션 관리"""

    # Redis 키 프리픽스
    SESSION_PREFIX = "sess"  # sess:{session_id}

    def __init__(self, ttl_minutes: int = 30):
        self.ttl_minutes = ttl_minutes
        self.ttl_seconds = ttl_minutes * 60

    async def create(self, user_id: str) -> str:
        """
        새 세션 생성

        Args:
            user_id: 사용자 ID

        Returns:
            session_id
        """
        session_id = str(uuid.uuid4())
        now = int(time.time())
        expires_at = now + self.ttl_seconds

        session_data = {
            "user_id": user_id,
            "created_at": now,
            "last_active": now,
            "expires": expires_at,
        }

        key = f"{self.SESSION_PREFIX}:{session_id}"
        await cache.set(key, session_data, ttl_seconds=self.ttl_seconds * 2)

        return session_id

    async def validate(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 검증

        Args:
            session_id: 세션 ID

        Returns:
            세션 데이터 dict 또는 None
        """
        key = f"{self.SESSION_PREFIX}:{session_id}"
        return await cache.get(key)

    async def validate_and_slide(
        self, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        세션 검증 및 슬라이딩 윈도우 갱신

        Args:
            session_id: 세션 ID

        Returns:
            갱신된 세션 데이터 dict 또는 None
        """
        key = f"{self.SESSION_PREFIX}:{session_id}"
        session_data = await cache.get(key)

        if not session_data:
            return None

        # 슬라이딩 윈도우: 현재 시간 기준으로 TTL 연장
        now = int(time.time())
        expires_at = now + self.ttl_seconds

        session_data.update(
            {
                "last_active": now,
                "expires": expires_at,
            }
        )

        await cache.set(key, session_data, ttl_seconds=self.ttl_seconds * 2)

        return session_data

    async def destroy(self, session_id: str) -> None:
        """
        세션 삭제

        Args:
            session_id: 세션 ID
        """
        key = f"{self.SESSION_PREFIX}:{session_id}"
        await cache.delete(key)

    async def destroy_user_sessions(self, user_id: str) -> None:
        """
        사용자의 모든 세션 삭제 (로그인 시 기존 세션 파괴)

        Args:
            user_id: 사용자 ID
        """
        pattern = f"{self.SESSION_PREFIX}:*"
        keys = await cache.redis.keys(pattern)

        for key in keys:
            session_data = await cache.get(key)
            if session_data and session_data.get("user_id") == user_id:
                await cache.delete(key)


session_manager = SessionManager(ttl_minutes=settings.SESSION_TTL_MIN)
