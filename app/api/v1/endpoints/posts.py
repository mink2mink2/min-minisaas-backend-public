"""
Posts endpoints
Board posts, SNS posts, feed
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.core.security import get_current_user

router = APIRouter()


# ==================== Board Posts ====================

@router.get("/board")
async def get_board_posts(
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = Query("latest", enum=["latest", "popular", "relevant"]),
    page: int = 1,
    limit: int = 20
):
    """Get board posts with filters"""
    # TODO: Fetch from database with filters
    return {"posts": [], "total": 0, "page": page}


@router.post("/board")
async def create_board_post(
    title: str,
    content: str,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Create a new board post"""
    # TODO: Save to database
    return {"post_id": "new-post-id"}


@router.get("/board/{post_id}")
async def get_board_post(post_id: str):
    """Get a specific board post"""
    # TODO: Fetch from database
    return {"post_id": post_id}


@router.put("/board/{post_id}")
async def update_board_post(
    post_id: str,
    title: str,
    content: str,
    current_user: dict = Depends(get_current_user)
):
    """Update a board post"""
    # TODO: Update in database
    return {"message": "Post updated"}


@router.delete("/board/{post_id}")
async def delete_board_post(post_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a board post (soft delete)"""
    # TODO: Soft delete
    return {"message": "Post deleted"}


# ==================== SNS Feed ====================

@router.get("/feed")
async def get_feed(
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get personalized feed"""
    # TODO: Fetch feed from followed users
    return {"posts": [], "page": page}


@router.post("/sns")
async def create_sns_post(
    content: str,
    media_urls: list = [],
    current_user: dict = Depends(get_current_user)
):
    """Create an SNS post"""
    # TODO: Save post
    return {"post_id": "new-sns-post-id"}


@router.post("/{post_id}/like")
async def like_post(post_id: str, current_user: dict = Depends(get_current_user)):
    """Like a post"""
    # TODO: Toggle like
    return {"liked": True}


@router.post("/{post_id}/bookmark")
async def bookmark_post(post_id: str, current_user: dict = Depends(get_current_user)):
    """Bookmark a post"""
    # TODO: Toggle bookmark
    return {"bookmarked": True}


# ==================== Comments ====================

@router.get("/{post_id}/comments")
async def get_comments(post_id: str, page: int = 1, limit: int = 20):
    """Get comments for a post"""
    # TODO: Fetch comments
    return {"comments": [], "page": page}


@router.post("/{post_id}/comments")
async def create_comment(
    post_id: str,
    content: str,
    parent_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Create a comment on a post"""
    # TODO: Save comment
    return {"comment_id": "new-comment-id"}
