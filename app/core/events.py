"""이벤트 버스 (Redis Pub/Sub)"""
import json
from dataclasses import dataclass, asdict
from datetime import datetime
import redis.asyncio as redis
from app.core.config import settings

@dataclass
class Event:
    event_type: str
    payload: dict
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))

class EventBus:
    def __init__(self):
        self.redis = None
    
    async def connect(self):
        self.redis = redis.from_url(settings.REDIS_URL)
    
    async def publish(self, event: Event):
        if self.redis:
            await self.redis.publish(event.event_type, event.to_json())

event_bus = EventBus()