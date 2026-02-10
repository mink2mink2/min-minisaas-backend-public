"""인증 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.user import UserCreate, UserLogin, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter()

@router.post("/register")
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    """회원가입"""
    service = AuthService(db)
    try:
        user = await service.register(data.email, data.password)
        return {"message": "가입 완료", "user_id": str(user.id)}
    except Exception:
        raise HTTPException(400, "이미 존재하는 이메일")

@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """로그인"""
    service = AuthService(db)
    result = await service.login(data.email, data.password)
    if not result:
        raise HTTPException(401, "이메일 또는 비밀번호 오류")
    return result