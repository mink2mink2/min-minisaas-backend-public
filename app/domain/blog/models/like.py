"""블로그 좋아요 모델"""
from sqlalchemy import Column, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import BaseModel


class BlogLike(BaseModel):
    """블로그 게시글 좋아요"""
    __tablename__ = "blog_likes"

    post_id = Column(UUID(as_uuid=True), ForeignKey("blog_posts.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_blog_likes_post_user"),
        Index("ix_blog_likes_post_id", "post_id"),
        Index("ix_blog_likes_user_id", "user_id"),
    )
