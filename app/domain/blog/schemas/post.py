"""블로그 게시글 스키마"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class AuthorBrief(BaseModel):
    """작성자 요약 정보"""
    id: UUID
    name: Optional[str] = None
    nickname: Optional[str] = None
    picture: Optional[str] = None
    username: Optional[str] = None

    class Config:
        from_attributes = True


class BlogPostCreate(BaseModel):
    """게시글 생성 요청"""
    title: str
    content: str
    category_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    excerpt: Optional[str] = None
    featured_image_url: Optional[str] = None
    is_published: bool = False


class BlogPostUpdate(BaseModel):
    """게시글 수정 요청"""
    title: Optional[str] = None
    content: Optional[str] = None
    category_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    excerpt: Optional[str] = None
    featured_image_url: Optional[str] = None
    is_published: Optional[bool] = None


class BlogPostListItem(BaseModel):
    """게시글 목록 아이템 (요약)"""
    id: UUID
    title: str
    slug: str
    excerpt: Optional[str]
    featured_image_url: Optional[str]
    author: AuthorBrief
    category_id: Optional[UUID] = None
    tags: List[str] = []
    published_at: Optional[datetime]
    view_count: int
    like_count: int
    comment_count: int
    is_liked: bool = False

    class Config:
        from_attributes = True


class BlogPostResponse(BaseModel):
    """게시글 상세 응답"""
    id: UUID
    title: str
    slug: str
    content: str
    excerpt: Optional[str]
    featured_image_url: Optional[str]
    author: AuthorBrief
    category_id: Optional[UUID] = None
    tags: List[str] = []
    is_published: bool
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    view_count: int
    like_count: int
    comment_count: int
    is_liked: bool = False
    author_subscriber_count: int = 0

    class Config:
        from_attributes = True
