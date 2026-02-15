"""게시판 카테고리 스키마"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID


class CategoryCreate(BaseModel):
    """카테고리 생성 요청"""
    name: str
    slug: str
    color: Optional[str] = "#000000"
    order_index: Optional[int] = 0


class CategoryUpdate(BaseModel):
    """카테고리 수정 요청"""
    name: Optional[str] = None
    slug: Optional[str] = None
    color: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    """카테고리 응답"""
    id: UUID
    name: str
    slug: str
    color: str
    order_index: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
