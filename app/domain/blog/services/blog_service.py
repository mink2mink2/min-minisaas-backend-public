"""블로그 비즈니스 로직"""
from uuid import UUID
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update, delete
from slugify import slugify

from app.domain.blog.models.post import BlogPost
from app.domain.blog.models.category import BlogCategory
from app.domain.blog.models.like import BlogLike
from app.domain.blog.models.subscription import BlogSubscription
from app.domain.auth.models.user import User
from app.core.events import event_bus, Event
from app.schemas.response import PaginatedResponse


class BlogPostCreatedEvent(Event):
    """블로그 게시글 생성 이벤트"""
    post_id: str
    author_id: str
    title: str
    tags: List[str]
    published_at: str


class BlogPostLikedEvent(Event):
    """블로그 게시글 좋아요 이벤트"""
    post_id: str
    user_id: str
    liked: bool  # True = liked, False = unliked


class BlogService:
    """블로그 도메인 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def generate_slug(title: str) -> str:
        """제목으로부터 slug 생성"""
        base_slug = slugify(title)
        return base_slug[:200]  # Max 200 chars

    async def create_post(
        self,
        author_id: UUID,
        title: str,
        content: str,
        category_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        excerpt: Optional[str] = None,
        featured_image_url: Optional[str] = None,
        is_published: bool = False,
    ) -> BlogPost:
        """블로그 게시글 생성"""
        slug = self.generate_slug(title)

        # Slug 중복 확인
        existing = await self.db.execute(
            select(BlogPost).where(BlogPost.slug == slug)
        )
        if existing.scalar():
            # 숫자를 추가하여 고유성 보장
            slug = f"{slug}-{datetime.utcnow().timestamp()}"

        post = BlogPost(
            title=title.strip(),
            slug=slug,
            content=content,
            category_id=category_id,
            excerpt=excerpt.strip() if excerpt else None,
            featured_image_url=featured_image_url,
            tags=tags or [],
            author_id=author_id,
            is_published=is_published,
            published_at=datetime.utcnow() if is_published else None,
        )

        self.db.add(post)
        await self.db.flush()
        await self.db.refresh(post)

        # 발행된 경우 이벤트 발행
        if is_published:
            await event_bus.emit(
                BlogPostCreatedEvent(
                    post_id=str(post.id),
                    author_id=str(author_id),
                    title=title,
                    tags=tags or [],
                    published_at=post.published_at.isoformat(),
                )
            )

        return post

    async def get_post(self, post_id: UUID) -> Optional[BlogPost]:
        """게시글 조회 (조회수 증가)"""
        result = await self.db.execute(
            select(BlogPost).where(
                and_(
                    BlogPost.id == post_id,
                    BlogPost.is_deleted.is_(False),
                )
            )
        )
        post = result.scalar()

        if post:
            # 조회수 증가
            await self.db.execute(
                update(BlogPost)
                .where(BlogPost.id == post_id)
                .values(view_count=BlogPost.view_count + 1)
            )
            await self.db.commit()

        return post

    async def list_feed(
        self, page: int = 1, limit: int = 20
    ) -> Tuple[List[BlogPost], int]:
        """전체 피드 조회 (발행된 글만)"""
        # 총 개수
        count_result = await self.db.execute(
            select(func.count())
            .select_from(BlogPost)
            .where(
                and_(
                    BlogPost.is_published.is_(True),
                    BlogPost.is_deleted.is_(False),
                )
            )
        )
        total = count_result.scalar() or 0

        # 페이징된 결과
        offset = (page - 1) * limit
        result = await self.db.execute(
            select(BlogPost)
            .where(
                and_(
                    BlogPost.is_published.is_(True),
                    BlogPost.is_deleted.is_(False),
                )
            )
            .order_by(BlogPost.published_at.desc())
            .offset(offset)
            .limit(limit)
        )
        posts = result.scalars().all()

        return list(posts), total

    async def list_user_blog(
        self, user_id: UUID, page: int = 1, limit: int = 20, include_drafts: bool = False
    ) -> Tuple[List[BlogPost], int]:
        """사용자 블로그 글 조회"""
        # 작성자 자신인 경우 draft 포함 가능
        conditions = [
            BlogPost.author_id == user_id,
            BlogPost.is_deleted.is_(False),
        ]

        if not include_drafts:
            conditions.append(BlogPost.is_published.is_(True))

        # 총 개수
        count_result = await self.db.execute(
            select(func.count())
            .select_from(BlogPost)
            .where(and_(*conditions))
        )
        total = count_result.scalar() or 0

        # 페이징된 결과
        offset = (page - 1) * limit
        result = await self.db.execute(
            select(BlogPost)
            .where(and_(*conditions))
            .order_by(BlogPost.published_at.desc().nullslast())
            .offset(offset)
            .limit(limit)
        )
        posts = result.scalars().all()

        return list(posts), total

    async def update_post(
        self,
        post_id: UUID,
        author_id: UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        excerpt: Optional[str] = None,
        featured_image_url: Optional[str] = None,
        is_published: Optional[bool] = None,
    ) -> Optional[BlogPost]:
        """게시글 수정 (작성자만)"""
        # 권한 확인
        result = await self.db.execute(
            select(BlogPost).where(BlogPost.id == post_id)
        )
        post = result.scalar()

        if not post or post.author_id != author_id:
            return None

        # 업데이트할 필드
        update_data = {}
        if title:
            update_data["title"] = title.strip()
            update_data["slug"] = self.generate_slug(title)
        if content:
            update_data["content"] = content
        if category_id is not None:
            update_data["category_id"] = category_id
        if tags is not None:
            update_data["tags"] = tags
        if excerpt is not None:
            update_data["excerpt"] = excerpt.strip() if excerpt else None
        if featured_image_url is not None:
            update_data["featured_image_url"] = featured_image_url
        if is_published is not None:
            update_data["is_published"] = is_published
            if is_published and not post.published_at:
                update_data["published_at"] = datetime.utcnow()

        await self.db.execute(
            update(BlogPost)
            .where(BlogPost.id == post_id)
            .values(**update_data)
        )
        await self.db.commit()
        await self.db.refresh(post)

        return post

    async def delete_post(self, post_id: UUID, author_id: UUID) -> bool:
        """게시글 삭제 (작성자만, soft delete)"""
        # 권한 확인
        result = await self.db.execute(
            select(BlogPost).where(BlogPost.id == post_id)
        )
        post = result.scalar()

        if not post or post.author_id != author_id:
            return False

        # Soft delete
        await self.db.execute(
            update(BlogPost)
            .where(BlogPost.id == post_id)
            .values(is_deleted=True)
        )
        await self.db.commit()

        return True

    async def search_posts(
        self, query: str, page: int = 1, limit: int = 20
    ) -> Tuple[List[BlogPost], int]:
        """게시글 검색 (발행된 글만)"""
        search_term = f"%{query}%"

        # 총 개수
        count_result = await self.db.execute(
            select(func.count())
            .select_from(BlogPost)
            .where(
                and_(
                    or_(
                        BlogPost.title.ilike(search_term),
                        BlogPost.content.ilike(search_term),
                        BlogPost.excerpt.ilike(search_term),
                    ),
                    BlogPost.is_published.is_(True),
                    BlogPost.is_deleted.is_(False),
                )
            )
        )
        total = count_result.scalar() or 0

        # 페이징된 결과
        offset = (page - 1) * limit
        result = await self.db.execute(
            select(BlogPost)
            .where(
                and_(
                    or_(
                        BlogPost.title.ilike(search_term),
                        BlogPost.content.ilike(search_term),
                        BlogPost.excerpt.ilike(search_term),
                    ),
                    BlogPost.is_published.is_(True),
                    BlogPost.is_deleted.is_(False),
                )
            )
            .order_by(BlogPost.published_at.desc())
            .offset(offset)
            .limit(limit)
        )
        posts = result.scalars().all()

        return list(posts), total

    async def like_post(self, post_id: UUID, user_id: UUID) -> bool:
        """게시글 좋아요"""
        # 이미 좋아요한 경우
        result = await self.db.execute(
            select(BlogLike).where(
                and_(
                    BlogLike.post_id == post_id,
                    BlogLike.user_id == user_id,
                )
            )
        )
        existing = result.scalar()

        if existing:
            return False  # 이미 좋아요함

        # 좋아요 추가
        like = BlogLike(post_id=post_id, user_id=user_id)
        self.db.add(like)

        # 좋아요 수 증가
        await self.db.execute(
            update(BlogPost)
            .where(BlogPost.id == post_id)
            .values(like_count=BlogPost.like_count + 1)
        )

        await self.db.commit()

        # 이벤트 발행
        await event_bus.emit(
            BlogPostLikedEvent(
                post_id=str(post_id),
                user_id=str(user_id),
                liked=True,
            )
        )

        return True

    async def unlike_post(self, post_id: UUID, user_id: UUID) -> bool:
        """게시글 좋아요 취소"""
        result = await self.db.execute(
            select(BlogLike).where(
                and_(
                    BlogLike.post_id == post_id,
                    BlogLike.user_id == user_id,
                )
            )
        )
        like = result.scalar()

        if not like:
            return False  # 좋아요하지 않음

        # 좋아요 제거
        await self.db.execute(
            delete(BlogLike).where(BlogLike.id == like.id)
        )

        # 좋아요 수 감소
        await self.db.execute(
            update(BlogPost)
            .where(BlogPost.id == post_id)
            .values(like_count=func.greatest(BlogPost.like_count - 1, 0))
        )

        await self.db.commit()

        # 이벤트 발행
        await event_bus.emit(
            BlogPostLikedEvent(
                post_id=str(post_id),
                user_id=str(user_id),
                liked=False,
            )
        )

        return True

    async def subscribe(self, subscriber_id: UUID, author_id: UUID) -> bool:
        """작성자 구독"""
        # 자신을 구독하려는 경우
        if subscriber_id == author_id:
            return False

        # 이미 구독한 경우
        result = await self.db.execute(
            select(BlogSubscription).where(
                and_(
                    BlogSubscription.subscriber_id == subscriber_id,
                    BlogSubscription.author_id == author_id,
                )
            )
        )
        existing = result.scalar()

        if existing:
            return False

        # 구독 추가
        subscription = BlogSubscription(
            subscriber_id=subscriber_id,
            author_id=author_id,
        )
        self.db.add(subscription)
        await self.db.commit()

        return True

    async def unsubscribe(self, subscriber_id: UUID, author_id: UUID) -> bool:
        """작성자 구독 취소"""
        result = await self.db.execute(
            select(BlogSubscription).where(
                and_(
                    BlogSubscription.subscriber_id == subscriber_id,
                    BlogSubscription.author_id == author_id,
                )
            )
        )
        subscription = result.scalar()

        if not subscription:
            return False

        # 구독 제거
        await self.db.execute(
            delete(BlogSubscription).where(BlogSubscription.id == subscription.id)
        )
        await self.db.commit()

        return True

    async def is_liked(self, post_id: UUID, user_id: UUID) -> bool:
        """게시글이 사용자에게 좋아요됐는지 확인"""
        result = await self.db.execute(
            select(BlogLike).where(
                and_(
                    BlogLike.post_id == post_id,
                    BlogLike.user_id == user_id,
                )
            )
        )
        return result.scalar() is not None

    async def is_subscribed(self, subscriber_id: UUID, author_id: UUID) -> bool:
        """사용자가 작성자를 구독했는지 확인"""
        result = await self.db.execute(
            select(BlogSubscription).where(
                and_(
                    BlogSubscription.subscriber_id == subscriber_id,
                    BlogSubscription.author_id == author_id,
                )
            )
        )
        return result.scalar() is not None

    async def get_subscriber_count(self, author_id: UUID) -> int:
        """작성자의 구독자 수"""
        result = await self.db.execute(
            select(func.count())
            .select_from(BlogSubscription)
            .where(BlogSubscription.author_id == author_id)
        )
        return result.scalar() or 0
