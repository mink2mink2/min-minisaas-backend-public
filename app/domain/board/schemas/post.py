"""게시글 스키마"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class AuthorBrief(BaseModel):
    """작성자 요약 정보"""
    id: UUID
    name: Optional[str] = None
    picture: Optional[str] = None
    username: Optional[str] = None

    class Config:
        from_attributes = True


class PostCreate(BaseModel):
    """게시글 생성 요청"""
    title: str
    content: str
    category_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = "published"


class PostUpdate(BaseModel):
    """게시글 수정 요청"""
    title: Optional[str] = None
    content: Optional[str] = None
    category_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None


class PostListItem(BaseModel):
    """게시글 목록 아이템 (요약)"""
    id: UUID
    title: str
    author: AuthorBrief
    category_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    view_count: int
    like_count: int
    comment_count: int
    bookmark_count: int
    is_liked: bool = False
    is_bookmarked: bool = False

    class Config:
        from_attributes = True


class PostResponse(BaseModel):
    """게시글 상세 응답"""
    id: UUID
    title: str
    content: str
    author: AuthorBrief
    category_id: Optional[UUID] = None
    tags: List[str] = []
    status: str
    created_at: datetime
    updated_at: datetime
    view_count: int
    like_count: int
    comment_count: int
    bookmark_count: int
    is_liked: bool = False
    is_bookmarked: bool = False

    class Config:
        from_attributes = True
