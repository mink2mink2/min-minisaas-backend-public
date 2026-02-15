"""게시글 서비스"""
import re
from uuid import UUID
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text, update
from sqlalchemy.dialects.postgresql import TSVECTOR
from app.domain.board.models.post import BoardPost, PostStatus
from app.domain.board.models.like_bookmark import PostLike, PostBookmark
from app.domain.auth.models.user import User
from app.core.cache import cache
from app.core.events import event_bus, Event
from app.schemas.response import PaginatedResponse


class PostService:
    """게시글 관련 비즈니스 로직"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_post_rate_limit(self, user_id: UUID) -> bool:
        """
        게시글 작성 레이트 제한 확인 (1분에 10개)
        Returns: True if allowed, False if rate limited
        """
        key = f"board:rate:post:{user_id}"
        count = await cache.get(key) or 0

        if count >= 10:
            return False

        # Redis INCR로 원자적 증가
        new_count = await cache.redis.incr(key)
        if new_count == 1:
            # 첫 증가시에만 TTL 설정 (1분)
            await cache.redis.expire(key, 60)

        return True

    @staticmethod
    def sanitize_content(raw: str, is_comment: bool = False) -> str:
        """
        컨텐츠 새니타이제이션 (HTML 태그 제거)

        Args:
            raw: 원본 컨텐츠
            is_comment: True면 모든 HTML 제거, False면 기본 태그 허용
        """
        if is_comment:
            # 모든 HTML 태그 제거
            return re.sub(r'<[^>]+>', '', raw)

        # 게시글: 기본 포맷팅 태그만 유지 (b, i, br, p)
        allowed_tags = ['<b>', '</b>', '<i>', '</i>', '<br>', '<br/>', '<p>', '</p>']

        # 먼저 모든 태그를 제거하고 허용된 것만 다시 추가
        # 간단한 방식: 위험한 태그만 제거
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # 스크립트
            r'<iframe[^>]*>.*?</iframe>',  # iframe
            r'on\w+\s*=',  # 이벤트 핸들러 (onload= 등)
        ]

        result = raw
        for pattern in dangerous_patterns:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE | re.DOTALL)

        return result

    async def create_post(
        self,
        author_id: UUID,
        title: str,
        content: str,
        category_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        status: str = "published"
    ) -> BoardPost:
        """
        게시글 생성

        Args:
            author_id: 작성자 ID
            title: 제목
            content: 내용
            category_id: 카테고리 ID
            tags: 태그 목록
            status: 상태 (draft, published, archived)
        """
        # 레이트 제한 확인
        if not await self.check_post_rate_limit(author_id):
            raise Exception("Rate limit exceeded: maximum 10 posts per minute")

        # 컨텐츠 새니타이제이션
        sanitized_content = self.sanitize_content(content, is_comment=False)

        post = BoardPost(
            title=title,
            content=sanitized_content,
            author_id=author_id,
            category_id=category_id,
            tags=tags or [],
            status=status
        )

        self.db.add(post)
        await self.db.commit()
        await self.db.refresh(post)

        # 이벤트 발행
        await event_bus.emit(Event(
            event_type="board.post.created",
            payload={
                "user_id": str(author_id),
                "post_id": str(post.id),
                "title": post.title,
                "category_id": str(post.category_id) if post.category_id else None
            }
        ))

        return post

    async def get_post(
        self,
        post_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[BoardPost]:
        """
        게시글 조회 (조회수 증가)

        Args:
            post_id: 게시글 ID
            user_id: 현재 사용자 ID (좋아요/북마크 확인용)
        """
        result = await self.db.execute(
            select(BoardPost).where(
                and_(BoardPost.id == post_id, BoardPost.is_deleted == False)
            )
        )
        post = result.scalar_one_or_none()

        if post:
            # 조회수 원자적 증가
            await self.db.execute(
                update(BoardPost)
                .where(BoardPost.id == post_id)
                .values(view_count=BoardPost.view_count + 1)
            )
            await self.db.commit()

            # 이벤트 발행
            if user_id:
                await event_bus.emit(Event(
                    event_type="board.post.viewed",
                    payload={
                        "user_id": str(user_id),
                        "post_id": str(post_id)
                    }
                ))

        return post

    async def list_posts(
        self,
        page: int = 1,
        limit: int = 20,
        category_id: Optional[UUID] = None,
        sort: str = "recent",  # recent, popular, trending
        user_id: Optional[UUID] = None
    ) -> Tuple[List[BoardPost], int]:
        """
        게시글 목록 조회 (페이지네이션 + 필터링 + 정렬)

        Args:
            page: 페이지 번호 (1부터 시작)
            limit: 페이지당 항목 수
            category_id: 카테고리 필터
            sort: 정렬 방식 (recent, popular, trending)
            user_id: 현재 사용자 ID (좋아요/북마크 확인용)
        """
        # 기본 쿼리
        query = select(BoardPost).where(
            and_(BoardPost.is_deleted == False, BoardPost.status == "published")
        )

        # 카테고리 필터
        if category_id:
            query = query.where(BoardPost.category_id == category_id)

        # 정렬
        if sort == "popular":
            query = query.order_by(BoardPost.like_count.desc())
        elif sort == "trending":
            query = query.order_by(
                (BoardPost.like_count + BoardPost.comment_count).desc()
            )
        else:  # recent (기본값)
            query = query.order_by(BoardPost.created_at.desc())

        # 총 개수
        count_result = await self.db.execute(
            select(func.count()).select_from(BoardPost).where(
                and_(BoardPost.is_deleted == False, BoardPost.status == "published")
            )
        )
        total = count_result.scalar() or 0

        # 페이지네이션
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        posts = result.scalars().all()

        return posts, total

    async def update_post(
        self,
        post_id: UUID,
        author_id: UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        status: Optional[str] = None
    ) -> Optional[BoardPost]:
        """게시글 수정 (작성자만)"""
        result = await self.db.execute(
            select(BoardPost).where(
                and_(BoardPost.id == post_id, BoardPost.author_id == author_id)
            )
        )
        post = result.scalar_one_or_none()

        if not post:
            return None

        if title:
            post.title = title
        if content:
            post.content = self.sanitize_content(content, is_comment=False)
        if category_id is not None:
            post.category_id = category_id
        if tags is not None:
            post.tags = tags
        if status:
            post.status = status

        self.db.add(post)
        await self.db.commit()
        await self.db.refresh(post)

        await event_bus.emit(Event(
            event_type="board.post.updated",
            payload={
                "user_id": str(author_id),
                "post_id": str(post_id)
            }
        ))

        return post

    async def delete_post(self, post_id: UUID, author_id: UUID) -> bool:
        """게시글 삭제 (소프트 삭제)"""
        result = await self.db.execute(
            select(BoardPost).where(
                and_(BoardPost.id == post_id, BoardPost.author_id == author_id)
            )
        )
        post = result.scalar_one_or_none()

        if not post:
            return False

        post.is_deleted = True
        self.db.add(post)
        await self.db.commit()

        await event_bus.emit(Event(
            event_type="board.post.deleted",
            payload={
                "user_id": str(author_id),
                "post_id": str(post_id)
            }
        ))

        return True

    async def search_posts(
        self,
        query: str,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[List[BoardPost], int]:
        """
        게시글 전문 검색 (PostgreSQL Full-Text Search)

        Primary: tsvector + plainto_tsquery
        Fallback: pg_trgm similarity (삼글자 유사도)
        """
        if not query or len(query.strip()) < 2:
            return [], 0

        # 안전한 쿼리 문자열 정제
        safe_query = query.strip()

        # PRIMARY: tsvector + plainto_tsquery
        fts_query = select(BoardPost).where(
            and_(
                BoardPost.is_deleted == False,
                BoardPost.status == "published",
                text(
                    "search_vector @@ plainto_tsquery('simple', :query)"
                )
            )
        ).params(query=safe_query)

        result = await self.db.execute(fts_query)
        posts = result.scalars().all()

        # FALLBACK: pg_trgm similarity (쿼리가 너무 짧으면 tsvector가 안 찰 수 있음)
        if not posts:
            fallback_query = select(BoardPost).where(
                and_(
                    BoardPost.is_deleted == False,
                    BoardPost.status == "published",
                    text(
                        "similarity(title || ' ' || content, :query) > 0.2"
                    )
                )
            ).order_by(
                text("similarity(title || ' ' || content, :query) DESC")
            ).params(query=safe_query)

            result = await self.db.execute(fallback_query)
            posts = result.scalars().all()

        # 총 개수
        total = len(posts)

        # 페이지네이션
        offset = (page - 1) * limit
        paginated_posts = posts[offset : offset + limit]

        return paginated_posts, total

    async def toggle_like(self, post_id: UUID, user_id: UUID) -> Tuple[bool, int]:
        """
        게시글 좋아요 토글

        Returns:
            (is_liked, like_count) tuple
        """
        # 기존 좋아요 확인
        result = await self.db.execute(
            select(PostLike).where(
                and_(PostLike.post_id == post_id, PostLike.user_id == user_id)
            )
        )
        like = result.scalar_one_or_none()

        if like:
            # 좋아요 제거
            await self.db.delete(like)
            await self.db.commit()

            # 카운트 감소
            await self.db.execute(
                update(BoardPost)
                .where(BoardPost.id == post_id)
                .values(like_count=BoardPost.like_count - 1)
            )
            await self.db.commit()

            await event_bus.emit(Event(
                event_type="board.post.liked",
                payload={
                    "user_id": str(user_id),
                    "post_id": str(post_id),
                    "liked": False
                }
            ))

            is_liked = False
        else:
            # 좋아요 추가
            like = PostLike(post_id=post_id, user_id=user_id)
            self.db.add(like)
            await self.db.commit()

            # 카운트 증가
            await self.db.execute(
                update(BoardPost)
                .where(BoardPost.id == post_id)
                .values(like_count=BoardPost.like_count + 1)
            )
            await self.db.commit()

            await event_bus.emit(Event(
                event_type="board.post.liked",
                payload={
                    "user_id": str(user_id),
                    "post_id": str(post_id),
                    "liked": True
                }
            ))

            is_liked = True

        # 최신 카운트 조회
        result = await self.db.execute(
            select(BoardPost.like_count).where(BoardPost.id == post_id)
        )
        like_count = result.scalar() or 0

        return is_liked, like_count

    async def toggle_bookmark(self, post_id: UUID, user_id: UUID) -> Tuple[bool, int]:
        """
        게시글 북마크 토글

        Returns:
            (is_bookmarked, bookmark_count) tuple
        """
        # 기존 북마크 확인
        result = await self.db.execute(
            select(PostBookmark).where(
                and_(PostBookmark.post_id == post_id, PostBookmark.user_id == user_id)
            )
        )
        bookmark = result.scalar_one_or_none()

        if bookmark:
            # 북마크 제거
            await self.db.delete(bookmark)
            await self.db.commit()

            # 카운트 감소
            await self.db.execute(
                update(BoardPost)
                .where(BoardPost.id == post_id)
                .values(bookmark_count=BoardPost.bookmark_count - 1)
            )
            await self.db.commit()

            is_bookmarked = False
        else:
            # 북마크 추가
            bookmark = PostBookmark(post_id=post_id, user_id=user_id)
            self.db.add(bookmark)
            await self.db.commit()

            # 카운트 증가
            await self.db.execute(
                update(BoardPost)
                .where(BoardPost.id == post_id)
                .values(bookmark_count=BoardPost.bookmark_count + 1)
            )
            await self.db.commit()

            is_bookmarked = True

        # 최신 카운트 조회
        result = await self.db.execute(
            select(BoardPost.bookmark_count).where(BoardPost.id == post_id)
        )
        bookmark_count = result.scalar() or 0

        return is_bookmarked, bookmark_count

    async def is_post_liked_by_user(self, post_id: UUID, user_id: UUID) -> bool:
        """사용자가 게시글에 좋아요를 눌렀는지 확인"""
        result = await self.db.execute(
            select(PostLike).where(
                and_(PostLike.post_id == post_id, PostLike.user_id == user_id)
            )
        )
        return result.scalar_one_or_none() is not None

    async def is_post_bookmarked_by_user(self, post_id: UUID, user_id: UUID) -> bool:
        """사용자가 게시글을 북마크했는지 확인"""
        result = await self.db.execute(
            select(PostBookmark).where(
                and_(PostBookmark.post_id == post_id, PostBookmark.user_id == user_id)
            )
        )
        return result.scalar_one_or_none() is not None
