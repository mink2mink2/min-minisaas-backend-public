"""보안 이벤트 로그"""
from sqlalchemy import Column, String, JSON, DateTime, Index, Text
from datetime import datetime
from app.models.base import BaseModel


class SecurityLog(BaseModel):
    """보안 이벤트 기록 (token reuse, suspicious activities 등)"""
    __tablename__ = "security_logs"

    user_id = Column(String(255), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)  # TOKEN_REUSE_DETECTED, DEVICE_SECRET_ROTATED 등
    device_id = Column(String(255), nullable=True, index=True)

    # 추가 정보
    details = Column(JSON, nullable=True)  # 이벤트별 상세 정보
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # 인덱스
    __table_args__ = (
        Index('idx_user_event_created', 'user_id', 'event_type', 'created_at'),
        Index('idx_device_event_created', 'device_id', 'event_type', 'created_at'),
    )
