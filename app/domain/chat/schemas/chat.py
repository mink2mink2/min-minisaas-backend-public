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


class ChatParticipantResponse(BaseModel):
    """채팅방 참여자 요약"""

    user_id: UUID
    name: Optional[str] = None
    picture: Optional[str] = None
    username: Optional[str] = None


class ChatLastMessagePreview(BaseModel):
    """채팅방 마지막 메시지 요약"""

    content: str
    sender_name: str
    created_at: datetime


class ChatRoomListItemResponse(BaseModel):
    """채팅방 목록 아이템"""

    id: UUID
    name: str
    is_group: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    member_count: int
    participants: List[ChatParticipantResponse]
    last_message: Optional[ChatLastMessagePreview] = None
    unread_count: int = 0


class ChatRoomListResponse(BaseModel):
    """채팅방 목록 페이징 응답"""

    items: List[ChatRoomListItemResponse]
    total: int
    page: int
    limit: int
    pages: int
    has_next: bool
    has_prev: bool


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


class ChatMessageListResponse(BaseModel):
    """채팅 메시지 목록 페이징 응답"""

    items: List[ChatMessageResponse]
    total: int
    page: int
    limit: int
    pages: int
    has_next: bool
    has_prev: bool


class ChatMessageBroadcast(BaseModel):
    """WS 브로드캐스트 payload"""

    event_type: str
    room_id: UUID
    message: ChatMessageResponse
    received_at: Optional[str] = None
