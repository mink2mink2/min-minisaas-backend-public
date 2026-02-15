"""댓글 엔드포인트"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional
from app.core.database import get_db
from app.api.v1.dependencies.api_key import verify_api_key
from app.api.v1.dependencies.auth import verify_any_platform, AuthResult
from app.domain.board.models.comment import Comment
from app.domain.auth.models.user import User
from app.domain.board.services.comment_service import CommentService
from app.domain.board.schemas.comment import (
    CommentCreate,
    CommentUpdate,
    CommentResponse,
    AuthorBrief,
)

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


def _build_comment_response(
    comment: Comment,
    author: AuthorBrief,
    is_liked: bool = False,
) -> CommentResponse:
    """댓글 객체를 CommentResponse로 변환"""
    replies = []
    if hasattr(comment, "replies"):
        for reply in comment.replies:
            # 재귀적으로 처리되지 않음 (replies는 최상위 댓글에서만)
            pass

    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        author=author,
        content=comment.content,
        depth=comment.depth,
        like_count=comment.like_count,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        replies=replies,
    )


@router.get("/{post_id}/comments", response_model=list[CommentResponse])
async def get_comments(
    post_id: UUID,
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    게시글의 모든 댓글 조회 (공개)

    트리 구조로 반환 (최상위 댓글 + 답댓글)
    """
    service = CommentService(db)
    comments = await service.get_comments(post_id)

    result = []
    for comment in comments:
        author = await _get_author_brief(comment.author_id, db)

        # 답댓글 처리
        replies = []
        if hasattr(comment, "replies"):
            for reply in comment.replies:
                reply_author = await _get_author_brief(reply.author_id, db)
                reply_response = CommentResponse(
                    id=reply.id,
                    post_id=reply.post_id,
                    author=reply_author,
                    content=reply.content,
                    depth=reply.depth,
                    like_count=reply.like_count,
                    created_at=reply.created_at,
                    updated_at=reply.updated_at,
                    replies=[],
                )
                replies.append(reply_response)

        comment_response = CommentResponse(
            id=comment.id,
            post_id=comment.post_id,
            author=author,
            content=comment.content,
            depth=comment.depth,
            like_count=comment.like_count,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            replies=replies,
        )
        result.append(comment_response)

    return result


@router.post("/{post_id}/comments", response_model=CommentResponse, status_code=201)
async def create_comment(
    post_id: UUID,
    data: CommentCreate,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    게시글에 댓글 작성 (인증 필수, 레이트 제한: 1초에 1개)

    - parent_comment_id: 답댓글인 경우 부모 댓글 ID
    """
    service = CommentService(db)
    author_id = UUID(auth.user_id)

    try:
        comment = await service.create_comment(
            post_id=post_id,
            author_id=author_id,
            content=data.content,
            parent_comment_id=data.parent_comment_id,
        )
    except Exception as e:
        if "Rate limit" in str(e):
            raise HTTPException(429, "Rate limit exceeded: maximum 1 comment per second")
        if "Maximum comment depth" in str(e):
            raise HTTPException(400, str(e))
        if "Parent comment not found" in str(e):
            raise HTTPException(404, "Parent comment not found")
        raise HTTPException(400, str(e))

    author = await _get_author_brief(author_id, db)
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        author=author,
        content=comment.content,
        depth=comment.depth,
        like_count=comment.like_count,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        replies=[],
    )


@router.post("/{post_id}/comments/{comment_id}/replies", response_model=CommentResponse, status_code=201)
async def create_reply(
    post_id: UUID,
    comment_id: UUID,
    data: CommentCreate,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    댓글에 답댓글 작성 (인증 필수)

    최대 2레벨까지만 가능
    """
    service = CommentService(db)
    author_id = UUID(auth.user_id)

    # comment_id를 parent_comment_id로 사용
    try:
        comment = await service.create_comment(
            post_id=post_id,
            author_id=author_id,
            content=data.content,
            parent_comment_id=comment_id,
        )
    except Exception as e:
        if "Rate limit" in str(e):
            raise HTTPException(429, "Rate limit exceeded: maximum 1 comment per second")
        if "Maximum comment depth" in str(e):
            raise HTTPException(400, "Maximum comment depth is 2 levels")
        if "Parent comment not found" in str(e):
            raise HTTPException(404, "Parent comment not found")
        raise HTTPException(400, str(e))

    author = await _get_author_brief(author_id, db)
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        author=author,
        content=comment.content,
        depth=comment.depth,
        like_count=comment.like_count,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        replies=[],
    )


@router.put("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: UUID,
    data: CommentUpdate,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """댓글 수정 (작성자만)"""
    service = CommentService(db)
    author_id = UUID(auth.user_id)

    comment = await service.update_comment(
        comment_id=comment_id,
        author_id=author_id,
        content=data.content,
    )

    if not comment:
        raise HTTPException(404, "Comment not found or not authorized")

    author = await _get_author_brief(comment.author_id, db)
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        author=author,
        content=comment.content,
        depth=comment.depth,
        like_count=comment.like_count,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        replies=[],
    )


@router.delete("/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: UUID,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """댓글 삭제 (작성자만, 소프트 삭제)"""
    service = CommentService(db)
    author_id = UUID(auth.user_id)

    deleted = await service.delete_comment(comment_id, author_id)
    if not deleted:
        raise HTTPException(404, "Comment not found or not authorized")
