"""채팅방 및 멤버 모델"""
from sqlalchemy import Boolean, Column, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


class ChatRoom(BaseModel):
    """채팅방"""

    __tablename__ = "chat_rooms"

    name = Column(String(120), nullable=False)
    is_group = Column(Boolean, default=False, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        Index("ix_chat_rooms_created_by", "created_by"),
        Index("ix_chat_rooms_created_at", "created_at"),
    )


class ChatRoomMember(BaseModel):
    """채팅방 멤버"""

    __tablename__ = "chat_room_members"

    room_id = Column(UUID(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False, default="member")

    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_chat_room_members_room_user"),
        Index("ix_chat_room_members_room_user", "room_id", "user_id"),
    )
