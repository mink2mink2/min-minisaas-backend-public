"""블로그 카테고리 스키마"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID


class CategoryCreate(BaseModel):
    """카테고리 생성 요청 (Admin only)"""
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool = True


class CategoryUpdate(BaseModel):
    """카테고리 수정 요청 (Admin only)"""
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    """카테고리 응답"""
    id: UUID
    name: str
    slug: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
