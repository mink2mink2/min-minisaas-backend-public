"""좋아요 및 북마크 엔드포인트"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.database import get_db
from app.api.v1.dependencies.api_key import verify_api_key
from app.api.v1.dependencies.auth import verify_any_platform, AuthResult
from app.domain.board.services.post_service import PostService
from app.domain.board.services.comment_service import CommentService

router = APIRouter()


@router.post("/{post_id}/like", response_model=dict)
async def like_post(
    post_id: UUID,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """게시글 좋아요 추가"""
    service = PostService(db)
    user_id = UUID(auth.user_id)

    try:
        is_liked, like_count = await service.toggle_like(post_id, user_id)
        return {
            "post_id": str(post_id),
            "is_liked": is_liked,
            "like_count": like_count,
        }
    except Exception as e:
        raise HTTPException(400, str(e))


@router.delete("/{post_id}/like", response_model=dict)
async def unlike_post(
    post_id: UUID,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """게시글 좋아요 제거 (또는 토글)"""
    service = PostService(db)
    user_id = UUID(auth.user_id)

    try:
        is_liked, like_count = await service.toggle_like(post_id, user_id)
        return {
            "post_id": str(post_id),
            "is_liked": is_liked,
            "like_count": like_count,
        }
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/{post_id}/bookmark", response_model=dict)
async def bookmark_post(
    post_id: UUID,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """게시글 북마크 추가"""
    service = PostService(db)
    user_id = UUID(auth.user_id)

    try:
        is_bookmarked, bookmark_count = await service.toggle_bookmark(post_id, user_id)
        return {
            "post_id": str(post_id),
            "is_bookmarked": is_bookmarked,
            "bookmark_count": bookmark_count,
        }
    except Exception as e:
        raise HTTPException(400, str(e))


@router.delete("/{post_id}/bookmark", response_model=dict)
async def unbookmark_post(
    post_id: UUID,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """게시글 북마크 제거 (또는 토글)"""
    service = PostService(db)
    user_id = UUID(auth.user_id)

    try:
        is_bookmarked, bookmark_count = await service.toggle_bookmark(post_id, user_id)
        return {
            "post_id": str(post_id),
            "is_bookmarked": is_bookmarked,
            "bookmark_count": bookmark_count,
        }
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/comments/{comment_id}/like", response_model=dict)
async def like_comment(
    comment_id: UUID,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """댓글 좋아요 추가"""
    service = CommentService(db)
    user_id = UUID(auth.user_id)

    try:
        is_liked, like_count = await service.toggle_comment_like(comment_id, user_id)
        return {
            "comment_id": str(comment_id),
            "is_liked": is_liked,
            "like_count": like_count,
        }
    except Exception as e:
        raise HTTPException(400, str(e))


@router.delete("/comments/{comment_id}/like", response_model=dict)
async def unlike_comment(
    comment_id: UUID,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """댓글 좋아요 제거 (또는 토글)"""
    service = CommentService(db)
    user_id = UUID(auth.user_id)

    try:
        is_liked, like_count = await service.toggle_comment_like(comment_id, user_id)
        return {
            "comment_id": str(comment_id),
            "is_liked": is_liked,
            "like_count": like_count,
        }
    except Exception as e:
        raise HTTPException(400, str(e))
