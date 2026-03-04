"""게시글 엔드포인트"""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional, List
from app.core.database import get_db
from app.api.v1.dependencies.api_key import verify_api_key
from app.api.v1.dependencies.auth import verify_any_platform, AuthResult
from app.domain.board.models.post import BoardPost
from app.domain.board.models.category import BoardCategory
from app.domain.auth.models.user import User
from app.domain.board.services.post_service import PostService
from app.domain.board.schemas.post import (
    PostCreate,
    PostUpdate,
    PostResponse,
    PostListItem,
    AuthorBrief,
)
from app.schemas.response import PaginatedResponse

router = APIRouter()


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


async def _add_reaction_flags(
    post: BoardPost,
    user_id: Optional[UUID],
    service: PostService,
) -> PostListItem | PostResponse:
    """게시글에 좋아요/북마크 플래그 추가"""
    is_liked = False
    is_bookmarked = False
    if user_id:
        is_liked = await service.is_post_liked_by_user(post.id, user_id)
        is_bookmarked = await service.is_post_bookmarked_by_user(post.id, user_id)
    return is_liked, is_bookmarked


@router.get("", response_model=dict)
async def list_posts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[UUID] = Query(None),
    sort: str = Query("recent", pattern="^(recent|popular|trending)$"),
    q: Optional[str] = Query(None, min_length=2, description="검색 쿼리"),
    request_user: Optional[AuthResult] = Depends(lambda: None),  # Optional auth
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    게시글 목록 조회 (공개, 검색 포함)

    - page: 페이지 번호 (1부터 시작)
    - limit: 페이지당 항목 수
    - category_id: 카테고리 필터 (선택사항)
    - sort: 정렬 방식 (recent, popular, trending)
    - q: 검색 쿼리 (선택사항, 최소 2글자)
    """
    service = PostService(db)
    user_id = None

    # 선택적 인증 처리
    try:
        request_user = await verify_any_platform(request, x_platform=request.headers.get("x-platform", "web"))
        user_id = UUID(request_user.user_id) if request_user else None
    except:
        pass

    # 검색 쿼리가 있으면 search_posts 사용, 없으면 list_posts 사용
    if q:
        posts, total = await service.search_posts(q, page=page, limit=limit)
    else:
        posts, total = await service.list_posts(
            page=page,
            limit=limit,
            category_id=category_id,
            sort=sort,
            user_id=user_id,
        )

    # 반응 정보 추가
    items = []
    for post in posts:
        author = await _get_author_brief(post.author_id, db)
        is_liked, is_bookmarked = await _add_reaction_flags(post, user_id, service)
        item = PostListItem(
            id=post.id,
            title=post.title,
            author=author,
            category_id=post.category_id,
            created_at=post.created_at,
            updated_at=post.updated_at,
            view_count=post.view_count,
            like_count=post.like_count,
            comment_count=post.comment_count,
            bookmark_count=post.bookmark_count,
            is_liked=is_liked,
            is_bookmarked=is_bookmarked,
        )
        items.append(item)

    return PaginatedResponse.create(items, total, page, limit).__dict__


@router.post("", response_model=PostResponse, status_code=201)
async def create_post(
    data: PostCreate,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """게시글 작성 (인증 필수, 레이트 제한: 1분에 10개)"""
    service = PostService(db)
    author_id = UUID(auth.user_id)

    try:
        post = await service.create_post(
            author_id=author_id,
            title=data.title,
            content=data.content,
            category_id=data.category_id,
            tags=data.tags or [],
            status=data.status or "published",
        )
    except Exception as e:
        if "Rate limit" in str(e):
            raise HTTPException(429, "Rate limit exceeded: maximum 10 posts per minute")
        raise HTTPException(400, str(e))

    author = await _get_author_brief(author_id, db)
    return PostResponse(
        id=post.id,
        title=post.title,
        content=post.content,
        author=author,
        category_id=post.category_id,
        tags=post.tags,
        status=post.status,
        created_at=post.created_at,
        updated_at=post.updated_at,
        view_count=post.view_count,
        like_count=post.like_count,
        comment_count=post.comment_count,
        bookmark_count=post.bookmark_count,
        is_liked=False,
        is_bookmarked=False,
    )


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: UUID,
    request_user: Optional[AuthResult] = Depends(lambda: None),  # Optional auth
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """게시글 상세 조회 (공개, 조회수 증가)"""
    service = PostService(db)
    user_id = None

    # 선택적 인증 처리
    try:
        auth = await verify_any_platform(request, x_platform=request.headers.get("x-platform", "web"))
        user_id = UUID(auth.user_id) if auth else None
    except:
        pass

    post = await service.get_post(post_id, user_id=user_id)
    if not post:
        raise HTTPException(404, "Post not found")

    author = await _get_author_brief(post.author_id, db)
    is_liked, is_bookmarked = await _add_reaction_flags(post, user_id, service)

    return PostResponse(
        id=post.id,
        title=post.title,
        content=post.content,
        author=author,
        category_id=post.category_id,
        tags=post.tags,
        status=post.status,
        created_at=post.created_at,
        updated_at=post.updated_at,
        view_count=post.view_count,
        like_count=post.like_count,
        comment_count=post.comment_count,
        bookmark_count=post.bookmark_count,
        is_liked=is_liked,
        is_bookmarked=is_bookmarked,
    )


@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: UUID,
    data: PostUpdate,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """게시글 수정 (작성자만)"""
    service = PostService(db)
    author_id = UUID(auth.user_id)

    post = await service.update_post(
        post_id=post_id,
        author_id=author_id,
        title=data.title,
        content=data.content,
        category_id=data.category_id,
        tags=data.tags,
        status=data.status,
    )

    if not post:
        raise HTTPException(404, "Post not found or not authorized")

    author = await _get_author_brief(post.author_id, db)
    is_liked, is_bookmarked = await _add_reaction_flags(post, author_id, service)

    return PostResponse(
        id=post.id,
        title=post.title,
        content=post.content,
        author=author,
        category_id=post.category_id,
        tags=post.tags,
        status=post.status,
        created_at=post.created_at,
        updated_at=post.updated_at,
        view_count=post.view_count,
        like_count=post.like_count,
        comment_count=post.comment_count,
        bookmark_count=post.bookmark_count,
        is_liked=is_liked,
        is_bookmarked=is_bookmarked,
    )


@router.delete("/{post_id}", status_code=204)
async def delete_post(
    post_id: UUID,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """게시글 삭제 (작성자만, 소프트 삭제)"""
    service = PostService(db)
    author_id = UUID(auth.user_id)

    deleted = await service.delete_post(post_id, author_id)
    if not deleted:
        raise HTTPException(404, "Post not found or not authorized")
