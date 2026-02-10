"""사용자 모델"""
from sqlalchemy import Column, String, Boolean, Integer
from app.models.base import BaseModel

class User(BaseModel):
    __tablename__ = "users"
    
    # 인증
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # 프로필
    username = Column(String(50), unique=True, nullable=True)
    display_name = Column(String(100), nullable=True)
    
    # 포인트
    point_balance = Column(Integer, default=0)