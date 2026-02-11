"""사용자 모델"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Text, DateTime
from app.models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    # 인증
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Firebase 로그인 사용자는 null

    # Firebase/OAuth
    firebase_uid = Column(String(128), unique=True, nullable=True, index=True)

    # 프로필
    name = Column(String(100), nullable=True)
    picture = Column(Text, nullable=True)
    username = Column(String(50), unique=True, nullable=True)

    # 계정 상태
    is_active = Column(Boolean, default=True)

    # 포인트
    points = Column(Integer, default=0)

    # 마지막 로그인
    last_login = Column(DateTime, nullable=True)