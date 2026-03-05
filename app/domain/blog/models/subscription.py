"""블로그 구독(팔로우) 모델"""
from sqlalchemy import Column, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import BaseModel


class BlogSubscription(BaseModel):
    """블로그 작성자 구독(팔로우)"""
    __tablename__ = "blog_subscriptions"

    subscriber_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("subscriber_id", "author_id", name="uq_blog_subscriptions_subscriber_author"),
        Index("ix_blog_subscriptions_subscriber_id", "subscriber_id"),
        Index("ix_blog_subscriptions_author_id", "author_id"),
    )
