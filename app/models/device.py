"""IoT 디바이스 모델"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import BaseModel
import uuid


class Device(BaseModel):
    __tablename__ = "devices"

    # Device ID (고유 식별자)
    device_id = Column(String(128), unique=True, nullable=False, index=True)

    # Device Secret (해시된 형태로 저장)
    device_secret_hash = Column(String(256), nullable=False)

    # Owner (사용자와의 관계)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Device Info
    name = Column(String(100), nullable=False)  # 디바이스 이름 (예: "거실 센서")
    device_type = Column(String(50), nullable=False)  # 디바이스 타입 (예: "sensor", "actuator")

    # Status
    is_active = Column(Boolean, default=True, index=True)

    # Metadata
    description = Column(Text, nullable=True)
    last_seen = Column(DateTime, nullable=True)  # 마지막 활동 시간
    secret_rotated_at = Column(DateTime, nullable=True)  # 마지막 시크릿 로테이션 시간
