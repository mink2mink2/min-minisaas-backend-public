"""블로그 엔드포인트"""
from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional, List

from app.core.database import get_db
from app.api.v1.dependencies.api_key import verify_api_key
from app.api.v1.dependencies.auth import verify_any_platform, AuthResult
from app.domain.blog.models.post import BlogPost
from app.domain.blog.models.category import BlogCategory
from app.domain.auth.models.user import User
from app.domain.blog.services.blog_service import BlogService
from app.domain.blog.schemas.post import (
    BlogPostCreate,
    BlogPostUpdate,
    BlogPostResponse,
    BlogPostListItem,
    AuthorBrief,
)
from app.domain.blog.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
)
from app.schemas.response import PaginatedResponse

router = APIRouter(prefix="/blog", tags=["blog"])


async def _get_optional_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_platform: Optional[str] = Header(None),
) -> Optional[AuthResult]:
    """선택적 인증: Authorization 헤더가 있으면 검증, 없으면 None"""
    if not authorization:
        return None
    try:
        return await verify_any_platform(request, x_platform=x_platform or "web")
    except:
        return None


async def _get_author_brief(user_id: UUID, db: AsyncSession) -> AuthorBrief:
    """사용자 정보를 AuthorBrief로 변환"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return AuthorBrief(id=user_id)
    return AuthorBrief(
        id=user.id,
        name=user.name,
        picture=user.picture,
        username=user.username,
    )


async def _build_post_response(
    post: BlogPost,
    user_id: Optional[UUID],
    service: BlogService,
    db: AsyncSession,
    include_subscriber_count: bool = False,
) -> dict:
    """게시글 응답 구성"""
    author = await _get_author_brief(post.author_id, db)
    is_liked = False
    author_subscriber_count = 0

    if user_id:
        is_liked = await service.is_liked(post.id, user_id)

    if include_subscriber_count:
        author_subscriber_count = await service.get_subscriber_count(post.author_id)

    return BlogPostResponse(
        id=post.id,
        title=post.title,
        slug=post.slug,
        content=post.content,
        excerpt=post.excerpt,
        featured_image_url=post.featured_image_url,
        author=author,
        category_id=post.category_id,
        tags=post.tags,
        is_published=post.is_published,
        published_at=post.published_at,
        created_at=post.created_at,
        updated_at=post.updated_at,
        view_count=post.view_count,
        like_count=post.like_count,
        comment_count=post.comment_count,
        is_liked=is_liked,
        author_subscriber_count=author_subscriber_count,
    )


# ============================================================================
# 카테고리 엔드포인트
# ============================================================================

@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """카테고리 목록 조회 (공개)"""
    result = await db.execute(
        select(BlogCategory).where(BlogCategory.is_active.is_(True)).order_by(BlogCategory.name)
    )
    categories = result.scalars().all()
    return [CategoryResponse.from_orm(cat) for cat in categories]


# ============================================================================
# 게시글 엔드포인트
# ============================================================================

@router.get("/feed", response_model=dict)
async def get_feed(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    request: Request = None,
    request_user: Optional[AuthResult] = Depends(_get_optional_user),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    블로그 피드 조회 (모든 사용자의 발행된 글)

    - page: 페이지 번호 (1부터 시작)
    - limit: 페이지당 항목 수
    """
    service = BlogService(db)
    user_id = UUID(request_user.user_id) if request_user else None

    posts, total = await service.list_feed(page=page, limit=limit)

    # 응답 구성
    items = []
    for post in posts:
        author = await _get_author_brief(post.author_id, db)
        is_liked = False
        if user_id:
            is_liked = await service.is_liked(post.id, user_id)

        item = BlogPostListItem(
            id=post.id,
            title=post.title,
            slug=post.slug,
            excerpt=post.excerpt,
            featured_image_url=post.featured_image_url,
            author=author,
            category_id=post.category_id,
            tags=post.tags,
            published_at=post.published_at,
            view_count=post.view_count,
            like_count=post.like_count,
            comment_count=post.comment_count,
            is_liked=is_liked,
        )
        items.append(item)

    return PaginatedResponse.create(items, total, page, limit).__dict__


@router.get("/users/{user_id}", response_model=dict)
async def get_user_blog(
    user_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    request: Request = None,
    request_user: Optional[AuthResult] = Depends(_get_optional_user),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    사용자 블로그 조회 (개인 블로그 페이지)

    - user_id: 조회할 사용자 ID
    - page: 페이지 번호
    - limit: 페이지당 항목 수
    """
    service = BlogService(db)
    current_user_id = UUID(request_user.user_id) if request_user else None

    # 사용자 정보 조회
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not found")

    # 사용자 블로그 글 조회
    include_drafts = current_user_id == user_id  # 자신의 draft 포함
    posts, total = await service.list_user_blog(
        user_id=user_id,
        page=page,
        limit=limit,
        include_drafts=include_drafts,
    )

    # 사용자 정보
    subscriber_count = await service.get_subscriber_count(user_id)
    is_subscribed = False
    if current_user_id and current_user_id != user_id:
        is_subscribed = await service.is_subscribed(current_user_id, user_id)

    # 글 목록
    items = []
    for post in posts:
        author = await _get_author_brief(post.author_id, db)
        is_liked = False
        if current_user_id:
            is_liked = await service.is_liked(post.id, current_user_id)

        item = BlogPostListItem(
            id=post.id,
            title=post.title,
            slug=post.slug,
            excerpt=post.excerpt,
            featured_image_url=post.featured_image_url,
            author=author,
            category_id=post.category_id,
            tags=post.tags,
            published_at=post.published_at,
            view_count=post.view_count,
            like_count=post.like_count,
            comment_count=post.comment_count,
            is_liked=is_liked,
        )
        items.append(item)

    return {
        "user": {
            "id": str(user.id),
            "name": user.name,
            "picture": user.picture,
            "username": user.username,
            "bio": user.bio if hasattr(user, "bio") else None,
            "subscriber_count": subscriber_count,
            "is_subscribed": is_subscribed,
        },
        "posts": PaginatedResponse.create(items, total, page, limit).__dict__,
    }


@router.get("/posts/{post_id}", response_model=dict)
async def get_post(
    post_id: UUID,
    request: Request = None,
    request_user: Optional[AuthResult] = Depends(_get_optional_user),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """게시글 상세 조회"""
    service = BlogService(db)
    user_id = UUID(request_user.user_id) if request_user else None

    post = await service.get_post(post_id)

    if not post or (not post.is_published and (not user_id or post.author_id != user_id)):
        raise HTTPException(404, "Post not found")

    return await _build_post_response(post, user_id, service, db, include_subscriber_count=True)


@router.post("/posts", response_model=dict, status_code=201)
async def create_post(
    data: BlogPostCreate,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """게시글 작성 (인증 필수)"""
    service = BlogService(db)
    author_id = UUID(auth.user_id)

    try:
        post = await service.create_post(
            author_id=author_id,
            title=data.title,
            content=data.content,
            category_id=data.category_id,
            tags=data.tags or [],
            excerpt=data.excerpt,
            featured_image_url=data.featured_image_url,
            is_published=data.is_published,
        )
    except Exception as e:
        raise HTTPException(400, str(e))

    return await _build_post_response(post, author_id, service, db, include_subscriber_count=False)


@router.put("/posts/{post_id}", response_model=dict)
async def update_post(
    post_id: UUID,
    data: BlogPostUpdate,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """게시글 수정 (작성자만)"""
    service = BlogService(db)
    author_id = UUID(auth.user_id)

    post = await service.update_post(
        post_id=post_id,
        author_id=author_id,
        title=data.title,
        content=data.content,
        category_id=data.category_id,
        tags=data.tags,
        excerpt=data.excerpt,
        featured_image_url=data.featured_image_url,
        is_published=data.is_published,
    )

    if not post:
        raise HTTPException(403, "Unauthorized")

    return await _build_post_response(post, author_id, service, db, include_subscriber_count=False)


@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(
    post_id: UUID,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """게시글 삭제 (작성자만)"""
    service = BlogService(db)
    author_id = UUID(auth.user_id)

    success = await service.delete_post(post_id, author_id)

    if not success:
        raise HTTPException(403, "Unauthorized")

    return None


@router.get("/search", response_model=dict)
async def search_posts(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    request: Request = None,
    request_user: Optional[AuthResult] = Depends(_get_optional_user),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """게시글 검색"""
    service = BlogService(db)
    user_id = UUID(request_user.user_id) if request_user else None

    posts, total = await service.search_posts(query=q, page=page, limit=limit)

    # 응답 구성
    items = []
    for post in posts:
        author = await _get_author_brief(post.author_id, db)
        is_liked = False
        if user_id:
            is_liked = await service.is_liked(post.id, user_id)

        item = BlogPostListItem(
            id=post.id,
            title=post.title,
            slug=post.slug,
            excerpt=post.excerpt,
            featured_image_url=post.featured_image_url,
            author=author,
            category_id=post.category_id,
            tags=post.tags,
            published_at=post.published_at,
            view_count=post.view_count,
            like_count=post.like_count,
            comment_count=post.comment_count,
            is_liked=is_liked,
        )
        items.append(item)

    return PaginatedResponse.create(items, total, page, limit).__dict__


# ============================================================================
# 반응 엔드포인트 (좋아요)
# ============================================================================

@router.post("/posts/{post_id}/like", status_code=200)
async def like_post(
    post_id: UUID,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """게시글 좋아요"""
    service = BlogService(db)
    user_id = UUID(auth.user_id)

    success = await service.like_post(post_id, user_id)

    if not success:
        raise HTTPException(400, "Already liked or post not found")

    return {"liked": True}


@router.delete("/posts/{post_id}/like", status_code=200)
async def unlike_post(
    post_id: UUID,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """게시글 좋아요 취소"""
    service = BlogService(db)
    user_id = UUID(auth.user_id)

    success = await service.unlike_post(post_id, user_id)

    if not success:
        raise HTTPException(400, "Not liked or post not found")

    return {"liked": False}


# ============================================================================
# 구독 엔드포인트 (팔로우)
# ============================================================================

@router.post("/users/{author_id}/subscribe", status_code=200)
async def subscribe_author(
    author_id: UUID,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """작성자 구독 (팔로우)"""
    service = BlogService(db)
    subscriber_id = UUID(auth.user_id)

    success = await service.subscribe(subscriber_id, author_id)

    if not success:
        raise HTTPException(400, "Already subscribed or invalid author")

    return {"subscribed": True}


@router.delete("/users/{author_id}/subscribe", status_code=200)
async def unsubscribe_author(
    author_id: UUID,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """작성자 구독 취소 (언팔로우)"""
    service = BlogService(db)
    subscriber_id = UUID(auth.user_id)

    success = await service.unsubscribe(subscriber_id, author_id)

    if not success:
        raise HTTPException(400, "Not subscribed or invalid author")

    return {"subscribed": False}
