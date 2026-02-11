"""사용자 스키마 (요청/응답 검증)"""
from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional
from uuid import UUID


class UserCreate(BaseModel):
    """회원가입 요청"""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    """로그인 요청"""

    email: EmailStr
    password: str
    client_type: Literal["web", "app"] = "web"


class TokenRefreshRequest(BaseModel):
    """토큰 갱신 요청"""

    refresh_token: str


class TokenResponse(BaseModel):
    """토큰 응답"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """사용자 정보 응답"""

    id: UUID
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    points: int = 0
    is_active: bool = True

    class Config:
        from_attributes = True