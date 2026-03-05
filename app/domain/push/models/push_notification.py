"""Push Notification 모델"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import BaseModel


class PushNotification(BaseModel):
    """푸시 알림"""
    __tablename__ = "push_notifications"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    event_type = Column(String(50), nullable=True)  # blog.post.created, chat.message, etc
    related_id = Column(UUID(as_uuid=True), nullable=True)  # post_id, message_id, etc
    is_read = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_push_notifications_user_id", "user_id"),
        Index("ix_push_notifications_event_type", "event_type"),
        Index("ix_push_notifications_created_at", "created_at"),
        Index("ix_push_notifications_is_read", "is_read"),
    )
