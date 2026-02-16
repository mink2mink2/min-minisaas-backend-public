"""FCM Token 모델"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import BaseModel


class FcmToken(BaseModel):
    """FCM 토큰 (Device Token)"""
    __tablename__ = "fcm_tokens"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(500), nullable=False, unique=True, index=True)
    platform = Column(String(20), nullable=False, index=True)  # android, ios, web
    device_name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_fcm_tokens_user_id", "user_id"),
        Index("ix_fcm_tokens_token", "token"),
        Index("ix_fcm_tokens_platform", "platform"),
    )
