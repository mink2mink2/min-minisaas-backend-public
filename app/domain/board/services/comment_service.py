"""댓글 서비스"""
import re
from uuid import UUID
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update
from app.domain.board.models.comment import Comment
from app.domain.board.models.post import BoardPost
from app.domain.board.models.like_bookmark import CommentLike
from app.core.cache import cache
from app.core.events import event_bus, Event


DELETED_CONTENT = "[삭제됨]"


class CommentService:
    """댓글 관련 비즈니스 로직"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_comment_rate_limit(self, user_id: UUID) -> bool:
        """
        댓글 작성 레이트 제한 (1초에 1개)
        Returns: True if allowed, False if rate limited
        """
        key = f"board:rate:comment:{user_id}"

        # SETNX (이미 존재하면 False 반환)
        result = await cache.redis.setnx(key, "1")

        if result:
            # 처음 생성됨, TTL 1초 설정
            await cache.redis.expire(key, 1)
            return True

        return False

    @staticmethod
    def sanitize_content(raw: str) -> str:
        """댓글 컨텐츠 새니타이제이션 (모든 HTML 태그 제거)"""
        return re.sub(r'<[^>]+>', '', raw)

    async def create_comment(
        self,
        post_id: UUID,
        author_id: UUID,
        content: str,
        parent_comment_id: Optional[UUID] = None
    ) -> Optional[Comment]:
        """
        댓글 생성 (최대 2레벨)

        Args:
            post_id: 게시글 ID
            author_id: 작성자 ID
            content: 댓글 내용
            parent_comment_id: 부모 댓글 ID (답댓글의 경우)
        """
        # 레이트 제한 확인
        if not await self.check_comment_rate_limit(author_id):
            raise Exception("Rate limit exceeded: maximum 1 comment per second")

        # 깊이 검증 (2레벨 이상 불가)
        depth = 0
        if parent_comment_id:
            result = await self.db.execute(
                select(Comment).where(Comment.id == parent_comment_id)
            )
            parent = result.scalar_one_or_none()

            if not parent:
                raise Exception("Parent comment not found")

            if parent.depth >= 1:
                raise Exception("Maximum comment depth is 2 levels")

            depth = 1

        # 컨텐츠 새니타이제이션
        sanitized_content = self.sanitize_content(content)

        comment = Comment(
            post_id=post_id,
            author_id=author_id,
            content=sanitized_content,
            parent_comment_id=parent_comment_id,
            depth=depth
        )

        self.db.add(comment)
        await self.db.commit()
        await self.db.refresh(comment)

        # 게시글의 댓글 수 증가
        await self.db.execute(
            update(BoardPost)
            .where(BoardPost.id == post_id)
            .values(comment_count=BoardPost.comment_count + 1)
        )
        await self.db.commit()

        # 이벤트 발행
        await event_bus.emit(Event(
            event_type="board.comment.created",
            payload={
                "user_id": str(author_id),
                "post_id": str(post_id),
                "comment_id": str(comment.id)
            }
        ))

        return comment

    async def get_comments(self, post_id: UUID) -> List[Comment]:
        """
        게시글의 모든 댓글 조회 (트리 구조)

        최상위 댓글을 먼저 조회하고, 각 댓글의 답댓글을 배치 로드
        """
        # 최상위 댓글 (depth=0) 조회
        result = await self.db.execute(
            select(Comment).where(
                and_(
                    Comment.post_id == post_id,
                    Comment.depth == 0,
                    Comment.is_deleted == False
                )
            ).order_by(Comment.created_at.asc())
        )
        top_level_comments = result.scalars().all()

        # 각 최상위 댓글에 대해 답댓글 로드
        for comment in top_level_comments:
            reply_result = await self.db.execute(
                select(Comment).where(
                    and_(
                        Comment.parent_comment_id == comment.id,
                        Comment.is_deleted == False
                    )
                ).order_by(Comment.created_at.asc())
            )
            replies = reply_result.scalars().all()

            # 삭제된 댓글 처리: 내용을 "[삭제됨]"으로 마스킹
            for reply in replies:
                if reply.is_deleted:
                    reply.content = DELETED_CONTENT

            # 동적 속성으로 replies 추가 (Schema에서 사용)
            comment.replies = replies

        # 최상위 댓글도 삭제 처리
        for comment in top_level_comments:
            if comment.is_deleted:
                comment.content = DELETED_CONTENT

        return top_level_comments

    async def update_comment(
        self,
        comment_id: UUID,
        author_id: UUID,
        content: str
    ) -> Optional[Comment]:
        """댓글 수정 (작성자만)"""
        result = await self.db.execute(
            select(Comment).where(
                and_(Comment.id == comment_id, Comment.author_id == author_id)
            )
        )
        comment = result.scalar_one_or_none()

        if not comment:
            return None

        comment.content = self.sanitize_content(content)
        self.db.add(comment)
        await self.db.commit()
        await self.db.refresh(comment)

        await event_bus.emit(Event(
            event_type="board.comment.updated",
            payload={
                "user_id": str(author_id),
                "comment_id": str(comment_id)
            }
        ))

        return comment

    async def delete_comment(self, comment_id: UUID, author_id: UUID) -> bool:
        """댓글 삭제 (소프트 삭제, 내용은 "[삭제됨]"으로 마스킹)"""
        result = await self.db.execute(
            select(Comment).where(
                and_(Comment.id == comment_id, Comment.author_id == author_id)
            )
        )
        comment = result.scalar_one_or_none()

        if not comment:
            return False

        # 소프트 삭제
        comment.is_deleted = True
        comment.content = DELETED_CONTENT
        self.db.add(comment)
        await self.db.commit()

        # 게시글의 댓글 수 감소
        await self.db.execute(
            update(BoardPost)
            .where(BoardPost.id == comment.post_id)
            .values(comment_count=BoardPost.comment_count - 1)
        )
        await self.db.commit()

        await event_bus.emit(Event(
            event_type="board.comment.deleted",
            payload={
                "user_id": str(author_id),
                "comment_id": str(comment_id)
            }
        ))

        return True

    async def toggle_comment_like(self, comment_id: UUID, user_id: UUID) -> Tuple[bool, int]:
        """
        댓글 좋아요 토글

        Returns:
            (is_liked, like_count) tuple
        """
        # 기존 좋아요 확인
        result = await self.db.execute(
            select(CommentLike).where(
                and_(CommentLike.comment_id == comment_id, CommentLike.user_id == user_id)
            )
        )
        like = result.scalar_one_or_none()

        if like:
            # 좋아요 제거
            await self.db.delete(like)
            await self.db.commit()

            # 카운트 감소
            await self.db.execute(
                update(Comment)
                .where(Comment.id == comment_id)
                .values(like_count=Comment.like_count - 1)
            )
            await self.db.commit()

            await event_bus.emit(Event(
                event_type="board.comment.liked",
                payload={
                    "user_id": str(user_id),
                    "comment_id": str(comment_id),
                    "liked": False
                }
            ))

            is_liked = False
        else:
            # 좋아요 추가
            like = CommentLike(comment_id=comment_id, user_id=user_id)
            self.db.add(like)
            await self.db.commit()

            # 카운트 증가
            await self.db.execute(
                update(Comment)
                .where(Comment.id == comment_id)
                .values(like_count=Comment.like_count + 1)
            )
            await self.db.commit()

            await event_bus.emit(Event(
                event_type="board.comment.liked",
                payload={
                    "user_id": str(user_id),
                    "comment_id": str(comment_id),
                    "liked": True
                }
            ))

            is_liked = True

        # 최신 카운트 조회
        result = await self.db.execute(
            select(Comment.like_count).where(Comment.id == comment_id)
        )
        like_count = result.scalar() or 0

        return is_liked, like_count

    async def is_comment_liked_by_user(self, comment_id: UUID, user_id: UUID) -> bool:
        """사용자가 댓글에 좋아요를 눌렀는지 확인"""
        result = await self.db.execute(
            select(CommentLike).where(
                and_(CommentLike.comment_id == comment_id, CommentLike.user_id == user_id)
            )
        )
        return result.scalar_one_or_none() is not None
