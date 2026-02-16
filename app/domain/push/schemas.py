"""푸시 알림 요청/응답 스키마"""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


# ============================================================================
# FCM Token Schemas
# ============================================================================

class FcmTokenRegister(BaseModel):
    """FCM 토큰 등록 요청"""
    token: str = Field(..., min_length=1, description="FCM 토큰")
    platform: str = Field(..., description="디바이스 플랫폼 (android, ios, web)")
    device_name: Optional[str] = Field(None, description="디바이스 이름")


class FcmTokenUpdate(BaseModel):
    """FCM 토큰 업데이트 요청"""
    platform: Optional[str] = Field(None, description="디바이스 플랫폼")
    device_name: Optional[str] = Field(None, description="디바이스 이름")


class FcmTokenResponse(BaseModel):
    """FCM 토큰 응답"""
    id: str
    token: str
    platform: str
    device_name: Optional[str]
    is_active: bool
    created_at: str


# ============================================================================
# Notification Schemas
# ============================================================================

class NotificationRead(BaseModel):
    """알림 읽음 표시 요청"""
    pass


class MarkAllAsReadRequest(BaseModel):
    """모든 알림 읽음 요청"""
    pass


class PushNotificationResponse(BaseModel):
    """푸시 알림 응답"""
    id: str
    user_id: str
    title: str
    body: str
    event_type: Optional[str]
    related_id: Optional[str]
    is_read: bool
    created_at: str


class PushNotificationListResponse(BaseModel):
    """푸시 알림 목록 응답"""
    items: List[PushNotificationResponse]
    total: int
    page: int
    limit: int
    has_next_page: bool


class UnreadCountResponse(BaseModel):
    """미읽은 알림 수 응답"""
    unread_count: int


class MarkAllAsReadResponse(BaseModel):
    """모든 알림 읽음 응답"""
    marked_count: int
