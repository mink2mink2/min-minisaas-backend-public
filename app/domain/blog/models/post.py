"""블로그 게시글 모델"""
from enum import Enum
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ARRAY, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.models.base import BaseModel


class BlogPost(BaseModel):
    """블로그 게시글"""
    __tablename__ = "blog_posts"

    # 기본 정보
    title = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    content = Column(Text, nullable=False)
    excerpt = Column(String(500), nullable=True)
    featured_image_url = Column(String(500), nullable=True)

    # 작성자
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # 카테고리 및 태그
    category_id = Column(UUID(as_uuid=True), ForeignKey("blog_categories.id"), nullable=True)
    tags = Column(ARRAY(String), default=[])

    # 발행 상태
    is_published = Column(Boolean, default=False)
    published_at = Column(DateTime, nullable=True)

    # 통계
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)

    # Soft delete는 BaseModel에서 상속받음 (is_deleted)

    __table_args__ = (
        Index("ix_blog_posts_author_id", "author_id"),
        Index("ix_blog_posts_published_at", "published_at"),
        Index("ix_blog_posts_like_count", "like_count"),
    )
