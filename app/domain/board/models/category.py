"""게시판 카테고리 모델"""
from sqlalchemy import Column, String, Integer, Boolean
from app.models.base import BaseModel


class BoardCategory(BaseModel):
    """게시판 카테고리"""
    __tablename__ = "board_categories"

    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    color = Column(String(7), default="#000000")  # Hex color code
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
