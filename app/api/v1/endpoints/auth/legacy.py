"""Legacy 인증 엔드포인트 (이메일+비밀번호)"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.domain.auth.schemas.user import UserCreate, UserLogin, TokenResponse, TokenRefreshRequest
from app.domain.auth.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth - Legacy"])


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
async def login(
    data: UserLogin,
    request: Request,
    user_agent: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """로그인"""
    service = AuthService(db)
    client_ip = request.client.host
    result = await service.login(
        data.email,
        data.password,
        client_type=data.client_type,
        user_agent=user_agent,
        ip=client_ip,
    )
    if not result:
        raise HTTPException(401, "이메일 또는 비밀번호 오류")
    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: TokenRefreshRequest,
    request: Request,
    user_agent: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """토큰 갱신"""
    service = AuthService(db)
    client_ip = request.client.host
    result = await service.refresh_token(
        data.refresh_token,
        user_agent=user_agent,
        ip=client_ip,
    )
    if not result:
        raise HTTPException(401, "유효하지 않은 리프레시 토큰입니다.")
    return result
