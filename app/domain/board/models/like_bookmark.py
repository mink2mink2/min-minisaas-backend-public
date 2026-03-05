"""좋아요와 북마크 모델"""
from sqlalchemy import Column, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import BaseModel


class PostLike(BaseModel):
    """게시글 좋아요"""
    __tablename__ = "post_likes"

    post_id = Column(UUID(as_uuid=True), ForeignKey("board_posts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_like"),
        Index("ix_post_likes_post_id", "post_id"),
        Index("ix_post_likes_user_id", "user_id"),
    )


class PostBookmark(BaseModel):
    """게시글 북마크"""
    __tablename__ = "post_bookmarks"

    post_id = Column(UUID(as_uuid=True), ForeignKey("board_posts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_bookmark"),
        Index("ix_post_bookmarks_post_id", "post_id"),
        Index("ix_post_bookmarks_user_id", "user_id"),
    )


class CommentLike(BaseModel):
    """댓글 좋아요"""
    __tablename__ = "comment_likes"

    comment_id = Column(UUID(as_uuid=True), ForeignKey("comments.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("comment_id", "user_id", name="uq_comment_like"),
        Index("ix_comment_likes_comment_id", "comment_id"),
        Index("ix_comment_likes_user_id", "user_id"),
    )
