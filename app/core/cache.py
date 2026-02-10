# api/app/core/cache.py
import redis.asyncio as redis
import json
from typing import Any, Optional

class RedisCache:
    def __init__(self, redis_url: str):
        self.redis = None
        self.redis_url = redis_url

    async def init(self):
        self.redis = await redis.from_url(self.redis_url)

    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 조회"""
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """캐시에 저장"""
        await self.redis.setex(
            key,
            ttl_seconds,
            json.dumps(value)
        )

    async def delete(self, key: str):
        """캐시 삭제"""
        await self.redis.delete(key)

    async def invalidate_pattern(self, pattern: str):
        """패턴으로 캐시 무효화"""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

# 전역 캐시 인스턴스
cache = RedisCache(settings.REDIS_URL)

@app.on_event("startup")
async def startup():
    await cache.init()