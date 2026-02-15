"""댓글 스키마"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class AuthorBrief(BaseModel):
    """작성자 요약 정보"""
    id: UUID
    name: Optional[str] = None
    picture: Optional[str] = None
    username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CommentCreate(BaseModel):
    """댓글 생성 요청"""
    content: str
    parent_comment_id: Optional[UUID] = None


class CommentUpdate(BaseModel):
    """댓글 수정 요청"""
    content: str


class CommentResponse(BaseModel):
    """댓글 응답 (자기참조)"""
    id: UUID
    post_id: UUID
    author: AuthorBrief
    content: str
    depth: int
    like_count: int
    created_at: datetime
    updated_at: datetime
    replies: List["CommentResponse"] = []

    model_config = ConfigDict(from_attributes=True)


# 자기참조 모델 재구성
CommentResponse.model_rebuild()
