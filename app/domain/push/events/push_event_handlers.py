"""푸시 알림 이벤트 핸들러"""
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.events import event_bus
from app.core.database import get_db_context
from app.domain.push.services.push_service import PushService

logger = logging.getLogger(__name__)


@event_bus.on("blog.post.created")
async def on_blog_post_created(event):
    """블로그 게시글 생성 이벤트 핸들러

    처리 항목:
    - 구독자들에게 알림 발송
    """
    try:
        post_id = event.payload.get("post_id")
        author_id = event.payload.get("author_id")
        title = event.payload.get("title")

        logger.info(f"Blog post created event: {post_id} by {author_id}")

        # DB 세션 획득
        async with get_db_context() as db:
            service = PushService(db)

            # 구독자들에게 알림 발송
            try:
                notif_count = await service.notify_subscribers(
                    author_id=UUID(author_id),
                    title=f"새 글: {title}",
                    body=f"구독 중인 작성자 {title}이 새로운 게시글을 발행했습니다",
                    event_type="blog.post.created",
                    related_id=UUID(post_id),
                )
                logger.info(f"Sent blog post created notification to {notif_count} subscribers")

            except Exception as e:
                logger.error(f"Error sending subscriber notifications: {e}")

    except Exception as e:
        logger.error(f"Error in on_blog_post_created: {e}")


@event_bus.on("blog.post.liked")
async def on_blog_post_liked(event):
    """블로그 게시글 좋아요 이벤트 핸들러

    처리 항목:
    - 작성자에게 알림 발송
    """
    try:
        post_id = event.payload.get("post_id")
        user_id = event.payload.get("user_id")
        liked = event.payload.get("liked")

        if not liked:
            return  # 좋아요 취소는 알림 없음

        logger.info(f"Blog post liked: {post_id} by {user_id}")

        async with get_db_context() as db:
            service = PushService(db)

            # 게시글 작성자 정보 조회
            from app.domain.blog.models.post import BlogPost
            from sqlalchemy import select

            result = await db.execute(select(BlogPost).where(BlogPost.id == UUID(post_id)))
            post = result.scalar_one_or_none()

            if post and post.author_id:
                try:
                    # 작성자에게 알림 발송
                    await service.notify_user(
                        user_id=post.author_id,
                        title="게시글에 좋아요가 달렸습니다",
                        body=f"'{post.title}' 게시글에 새로운 좋아요가 있습니다",
                        event_type="blog.post.liked",
                        related_id=UUID(post_id),
                    )
                    logger.info(f"Sent blog post liked notification to author {post.author_id}")

                except Exception as e:
                    logger.error(f"Error sending author notification: {e}")

    except Exception as e:
        logger.error(f"Error in on_blog_post_liked: {e}")


@event_bus.on("chat.message.created")
async def on_chat_message_created(event):
    """채팅 메시지 생성 이벤트 핸들러

    처리 항목:
    - 채팅방 멤버들에게 알림 발송
    """
    try:
        room_id = event.payload.get("room_id")
        message_id = event.payload.get("message_id")
        sender_id = event.payload.get("sender_id")
        content = event.payload.get("content")

        logger.info(f"Chat message created: {message_id} in room {room_id}")

        async with get_db_context() as db:
            # 채팅방 멤버 조회
            from app.domain.chat.models.room import ChatRoom
            from sqlalchemy import select

            result = await db.execute(select(ChatRoom).where(ChatRoom.id == UUID(room_id)))
            room = result.scalar_one_or_none()

            if room:
                # 발신자 제외한 멤버들에게 알림
                room_member_ids = [m.user_id for m in room.members if m.user_id != UUID(sender_id)]

                if room_member_ids:
                    service = PushService(db)

                    try:
                        title = room.name or "새 메시지"
                        body = content[:100] if len(content) > 100 else content

                        await service.notify_users(
                            user_ids=room_member_ids,
                            title=title,
                            body=body,
                            event_type="chat.message.created",
                            related_id=UUID(room_id),
                        )
                        logger.info(f"Sent chat message notification to {len(room_member_ids)} members")

                    except Exception as e:
                        logger.error(f"Error sending chat message notifications: {e}")

    except Exception as e:
        logger.error(f"Error in on_chat_message_created: {e}")


@event_bus.on("board.post.liked")
async def on_board_post_liked(event):
    """게시판 게시글 좋아요 이벤트 핸들러

    처리 항목:
    - 작성자에게 알림 발송
    """
    try:
        post_id = event.payload.get("post_id")
        user_id = event.payload.get("user_id")
        liked = event.payload.get("liked")

        if not liked:
            return  # 좋아요 취소는 알림 없음

        logger.info(f"Board post liked: {post_id} by {user_id}")

        async with get_db_context() as db:
            service = PushService(db)

            # 게시글 작성자 정보 조회
            from app.domain.board.models.post import BoardPost
            from sqlalchemy import select

            result = await db.execute(select(BoardPost).where(BoardPost.id == UUID(post_id)))
            post = result.scalar_one_or_none()

            if post and post.user_id:
                try:
                    await service.notify_user(
                        user_id=post.user_id,
                        title="게시글에 좋아요가 달렸습니다",
                        body=f"'{post.title}' 게시글에 새로운 좋아요가 있습니다",
                        event_type="board.post.liked",
                        related_id=UUID(post_id),
                    )
                    logger.info(f"Sent board post liked notification to author {post.user_id}")

                except Exception as e:
                    logger.error(f"Error sending board post liked notification: {e}")

    except Exception as e:
        logger.error(f"Error in on_board_post_liked: {e}")


@event_bus.on("board.comment.created")
async def on_board_comment_created(event):
    """게시판 댓글 생성 이벤트 핸들러

    처리 항목:
    - 게시글 작성자에게 알림 발송
    """
    try:
        post_id = event.payload.get("post_id")
        user_id = event.payload.get("user_id")
        comment_id = event.payload.get("comment_id")

        logger.info(f"Board comment created: {comment_id} on post {post_id}")

        async with get_db_context() as db:
            service = PushService(db)

            # 게시글 작성자 정보 조회
            from app.domain.board.models.post import BoardPost
            from sqlalchemy import select

            result = await db.execute(select(BoardPost).where(BoardPost.id == UUID(post_id)))
            post = result.scalar_one_or_none()

            if post and post.user_id and post.user_id != UUID(user_id):
                try:
                    await service.notify_user(
                        user_id=post.user_id,
                        title="게시글에 댓글이 달렸습니다",
                        body=f"'{post.title}' 게시글에 새로운 댓글이 있습니다",
                        event_type="board.comment.created",
                        related_id=UUID(post_id),
                    )
                    logger.info(f"Sent board comment created notification to author {post.user_id}")

                except Exception as e:
                    logger.error(f"Error sending board comment created notification: {e}")

    except Exception as e:
        logger.error(f"Error in on_board_comment_created: {e}")
