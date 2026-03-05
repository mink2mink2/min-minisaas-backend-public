"""댓글 모델"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import BaseModel


class Comment(BaseModel):
    """게시물 댓글 (최대 2레벨)"""
    __tablename__ = "comments"

    post_id = Column(UUID(as_uuid=True), ForeignKey("board_posts.id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # 부모 댓글 (답댓글)
    parent_comment_id = Column(UUID(as_uuid=True), ForeignKey("comments.id"), nullable=True)

    content = Column(Text, nullable=False)

    # 깊이 (0=최상위, 1=답댓글)
    depth = Column(Integer, default=0)

    # 반응 통계
    like_count = Column(Integer, default=0)

    # 인덱스
    __table_args__ = (
        Index("ix_comments_post_id", "post_id"),
        Index("ix_comments_author_id", "author_id"),
        Index("ix_comments_parent_comment_id", "parent_comment_id"),
        Index("ix_comments_created_at", "created_at"),
    )
