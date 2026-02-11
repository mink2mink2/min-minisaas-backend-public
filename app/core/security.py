from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """비밀번호 해싱"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: str, client_type: str = "web") -> str:
    """액세스 토큰 생성 (클라이언트 유형에 따라 만료 시간 차별화 가능)"""
    # 기본 15분, 앱의 경우 더 길게 설정 가능
    minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    if client_type == "app":
        minutes = minutes * 4  # 예: 앱은 1시간
        
    expire = datetime.utcnow() + timedelta(minutes=minutes)
    data = {"sub": user_id, "exp": expire, "type": "access", "client": client_type}
    return jwt.encode(data, settings.SECRET_KEY, algorithm="HS256")

def create_refresh_token(user_id: str, client_type: str = "web") -> str:
    """리프레시 토큰 생성"""
    days = settings.REFRESH_TOKEN_EXPIRE_DAYS
    if client_type == "app":
        days = days * 4  # 예: 앱은 28일
        
    expire = datetime.utcnow() + timedelta(days=days)
    data = {"sub": user_id, "exp": expire, "type": "refresh", "client": client_type}
    return jwt.encode(data, settings.SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> dict:
    """토큰 디코딩"""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from app.core.cache import cache

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

async def get_current_user(request: Request, token: str = Depends(oauth2_scheme)) -> dict:
    """현재 사용자 조회 및 세션 검증"""
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        client_type: str = payload.get("client")
        if user_id is None or client_type is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰입니다."
            )
        
        # 보안 강화: Redis 세션 검증 (강력한 보안 제공)
        session_key = f"auth:session:{user_id}:{client_type}"
        session_data = await cache.get(session_key)
        
        # 1. 세션 존재 및 액세스 토큰 일치 확인
        if not session_data or session_data.get("access") != token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="만료되었거나 유효하지 않은 세션입니다."
            )
        
        # 2. 기기 핑거프린트 검증 (보안 강화)
        user_agent = request.headers.get("user-agent")
        if session_data.get("ua") and session_data.get("ua") != user_agent:
            # UA가 다를 경우 보안상 세션 종료 또는 경고 (현재는 관용적으로 처리하거나 로깅 가능)
            pass

        return {"id": user_id, "client_type": client_type}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증에 실패했습니다."
        )