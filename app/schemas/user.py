"""사용자 스키마 (요청/응답 검증)"""
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    """회원가입 요청"""
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class UserLogin(BaseModel):
    """로그인 요청"""
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """토큰 응답"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"