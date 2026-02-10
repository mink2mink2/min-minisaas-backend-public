# 기존 코드 아래에 추가

from datetime import datetime, timedelta
from jose import jwt

def create_access_token(user_id: str) -> str:
    """액세스 토큰 생성 (15분)"""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    data = {"sub": user_id, "exp": expire, "type": "access"}
    return jwt.encode(data, settings.SECRET_KEY, algorithm="HS256")

def create_refresh_token(user_id: str) -> str:
    """리프레시 토큰 생성 (7일)"""
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    data = {"sub": user_id, "exp": expire, "type": "refresh"}
    return jwt.encode(data, settings.SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> dict:
    """토큰 디코딩"""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])