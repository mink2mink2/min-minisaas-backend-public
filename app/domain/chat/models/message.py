"""채팅 메시지 모델"""
from sqlalchemy import Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


class ChatMessage(BaseModel):
    """채팅 메시지"""

    __tablename__ = "chat_messages"

    room_id = Column(UUID(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), nullable=False, default="text")

    __table_args__ = (
        Index("ix_chat_messages_room_created_at", "room_id", "created_at"),
        Index("ix_chat_messages_sender_id", "sender_id"),
    )
