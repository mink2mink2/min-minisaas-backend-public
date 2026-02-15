"""이벤트 버스 및 이벤트 정의"""
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Callable, List, Dict
import redis.asyncio as redis
from app.core.config import settings

# ============================================================================
# Event 클래스들
# ============================================================================

@dataclass
class Event:
    """기본 이벤트"""
    event_type: str
    payload: dict
    timestamp: str = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass
class UserLoggedInEvent(Event):
    """사용자 로그인 완료 이벤트"""
    def __init__(self, user_id: str, email: str, platform: str, is_new_user: bool = False):
        super().__init__(
            event_type="user.logged_in",
            payload={
                "user_id": user_id,
                "email": email,
                "platform": platform,
                "is_new_user": is_new_user
            }
        )


@dataclass
class UserCreatedEvent(Event):
    """신규 사용자 생성 이벤트"""
    def __init__(self, user_id: str, email: str):
        super().__init__(
            event_type="user.created",
            payload={
                "user_id": user_id,
                "email": email
            }
        )


@dataclass
class UserLoggedOutEvent(Event):
    """사용자 로그아웃 이벤트"""
    def __init__(self, user_id: str, platform: str):
        super().__init__(
            event_type="user.logged_out",
            payload={
                "user_id": user_id,
                "platform": platform
            }
        )


@dataclass
class SecurityAlertEvent(Event):
    """보안 경고 이벤트"""
    def __init__(self, user_id: str, event_type: str, severity: str, details: dict = None, device_id: str = None):
        super().__init__(
            event_type="security.alert",
            payload={
                "user_id": user_id,
                "event_type": event_type,
                "severity": severity,
                "details": details or {},
                "device_id": device_id
            }
        )


@dataclass
class BoardPostCreatedEvent(Event):
    """게시글 생성 이벤트"""
    def __init__(self, user_id: str, post_id: str, title: str, category_id: str = None):
        super().__init__(
            event_type="board.post.created",
            payload={
                "user_id": user_id,
                "post_id": post_id,
                "title": title,
                "category_id": category_id
            }
        )


@dataclass
class BoardPostUpdatedEvent(Event):
    """게시글 수정 이벤트"""
    def __init__(self, user_id: str, post_id: str):
        super().__init__(
            event_type="board.post.updated",
            payload={
                "user_id": user_id,
                "post_id": post_id
            }
        )


@dataclass
class BoardPostDeletedEvent(Event):
    """게시글 삭제 이벤트"""
    def __init__(self, user_id: str, post_id: str):
        super().__init__(
            event_type="board.post.deleted",
            payload={
                "user_id": user_id,
                "post_id": post_id
            }
        )


@dataclass
class BoardPostViewedEvent(Event):
    """게시글 조회 이벤트"""
    def __init__(self, user_id: str, post_id: str):
        super().__init__(
            event_type="board.post.viewed",
            payload={
                "user_id": user_id,
                "post_id": post_id
            }
        )


@dataclass
class BoardPostLikedEvent(Event):
    """게시글 좋아요 이벤트"""
    def __init__(self, user_id: str, post_id: str, liked: bool):
        super().__init__(
            event_type="board.post.liked",
            payload={
                "user_id": user_id,
                "post_id": post_id,
                "liked": liked
            }
        )


@dataclass
class BoardCommentCreatedEvent(Event):
    """댓글 생성 이벤트"""
    def __init__(self, user_id: str, post_id: str, comment_id: str):
        super().__init__(
            event_type="board.comment.created",
            payload={
                "user_id": user_id,
                "post_id": post_id,
                "comment_id": comment_id
            }
        )


@dataclass
class BoardCommentUpdatedEvent(Event):
    """댓글 수정 이벤트"""
    def __init__(self, user_id: str, comment_id: str):
        super().__init__(
            event_type="board.comment.updated",
            payload={
                "user_id": user_id,
                "comment_id": comment_id
            }
        )


@dataclass
class BoardCommentDeletedEvent(Event):
    """댓글 삭제 이벤트"""
    def __init__(self, user_id: str, comment_id: str):
        super().__init__(
            event_type="board.comment.deleted",
            payload={
                "user_id": user_id,
                "comment_id": comment_id
            }
        )


@dataclass
class BoardCommentLikedEvent(Event):
    """댓글 좋아요 이벤트"""
    def __init__(self, user_id: str, comment_id: str, liked: bool):
        super().__init__(
            event_type="board.comment.liked",
            payload={
                "user_id": user_id,
                "comment_id": comment_id,
                "liked": liked
            }
        )

# ============================================================================
# Event Bus
# ============================================================================

class EventBus:
    """비동기 Event Bus (Redis Pub/Sub + 로컬 핸들러)"""

    def __init__(self):
        self.redis = None
        self._subscribers: Dict[str, List[Callable]] = {}

    async def connect(self):
        """Redis 연결"""
        try:
            self.redis = redis.from_url(settings.REDIS_URL_WITH_AUTH)
        except Exception:
            self.redis = None

    def subscribe(self, event_type: str, handler: Callable):
        """이벤트 핸들러 등록"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def emit(self, event: Event):
        """이벤트 발행 (Redis Pub/Sub + 로컬 핸들러)"""
        # Redis로 발행
        if self.redis:
            try:
                await self.redis.publish(event.event_type, event.to_json())
            except Exception:
                pass

        # 로컬 핸들러 실행 (비동기)
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                if hasattr(handler, '__call__'):
                    # 핸들러가 async 함수인 경우
                    import asyncio
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(event))
                    else:
                        handler(event)
            except Exception:
                pass

event_bus = EventBus()
