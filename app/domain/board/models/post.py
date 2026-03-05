"""게시글 모델"""
from enum import Enum
from sqlalchemy import Column, String, Text, Integer, ARRAY, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
import uuid
from app.models.base import BaseModel


class PostStatus(str, Enum):
    """게시글 상태"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class BoardPost(BaseModel):
    """게시판 게시글"""
    __tablename__ = "board_posts"

    title = Column(String(200), nullable=False, index=True)
    content = Column(Text, nullable=False)
    status = Column(String(20), default=PostStatus.PUBLISHED.value)

    # 작성자
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # 카테고리 (선택사항)
    category_id = Column(UUID(as_uuid=True), ForeignKey("board_categories.id"), nullable=True)

    # 메타데이터
    tags = Column(ARRAY(String), default=[])

    # 조회/반응 통계
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    bookmark_count = Column(Integer, default=0)

    # 전문 검색 벡터 (PostgreSQL tsvector)
    search_vector = Column(TSVECTOR, nullable=True)

    # 인덱스
    __table_args__ = (
        Index("ix_board_posts_author_id", "author_id"),
        Index("ix_board_posts_category_id", "category_id"),
        Index("ix_board_posts_status", "status"),
        Index("ix_board_posts_created_at", "created_at"),
    )
