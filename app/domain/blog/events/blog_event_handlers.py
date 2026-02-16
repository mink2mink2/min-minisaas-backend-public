"""블로그 도메인 이벤트 핸들러"""
import logging
from app.core.events import event_bus, Event
from app.domain.blog.services.blog_service import BlogPostCreatedEvent, BlogPostLikedEvent

logger = logging.getLogger(__name__)


@event_bus.on("blog.post.created")
async def on_post_created(event: BlogPostCreatedEvent):
    """블로그 게시글 생성 이벤트 핸들러

    처리 항목:
    - 검색 인덱싱 (향후 구현)
    - 구독자 피드 갱신 (향후 구현)
    - 알림 발송 (향후 구현)
    """
    try:
        logger.info(f"Blog post created: {event.post_id} by {event.author_id}")

        # TODO: 검색 인덱싱
        # await search_engine.index_post(event.post_id, event.title, event.tags)

        # TODO: 구독자 알림
        # await notification_service.notify_subscribers(event.author_id, event)

    except Exception as e:
        logger.error(f"Error in on_post_created: {e}")


@event_bus.on("blog.post.liked")
async def on_post_liked(event: BlogPostLikedEvent):
    """블로그 게시글 좋아요 이벤트 핸들러

    처리 항목:
    - 작성자 알림 (향후 구현)
    - 좋아요 통계 업데이트 (이미 Service에서 처리)
    """
    try:
        logger.info(f"Blog post {'liked' if event.liked else 'unliked'}: {event.post_id} by {event.user_id}")

        # TODO: 작성자에게 알림
        # if event.liked:
        #     await notification_service.notify_author_liked(event.post_id, event.user_id)

    except Exception as e:
        logger.error(f"Error in on_post_liked: {e}")
