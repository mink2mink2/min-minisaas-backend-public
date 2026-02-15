"""채팅 스키마"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRoomCreate(BaseModel):
    """채팅방 생성 요청"""

    name: str = Field(min_length=1, max_length=120)
    is_group: bool = False
    member_ids: List[UUID] = Field(default_factory=list)


class ChatRoomResponse(BaseModel):
    """채팅방 응답"""

    id: UUID
    name: str
    is_group: bool
    created_by: UUID
    member_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    """메시지 전송 요청"""

    content: str = Field(min_length=1, max_length=4000)


class ChatMessageResponse(BaseModel):
    """메시지 응답"""

    id: UUID
    room_id: UUID
    sender_id: UUID
    content: str
    message_type: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatMessageBroadcast(BaseModel):
    """WS 브로드캐스트 payload"""

    event_type: str
    room_id: UUID
    message: ChatMessageResponse
    received_at: Optional[str] = None
