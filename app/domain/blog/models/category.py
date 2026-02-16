"""블로그 카테고리 모델"""
from sqlalchemy import Column, String, Text, Boolean, Index
from app.models.base import BaseModel


class BlogCategory(BaseModel):
    """블로그 카테고리"""
    __tablename__ = "blog_categories"

    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index("ix_blog_categories_name", "name"),
    )
