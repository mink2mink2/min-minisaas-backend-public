"""CSRF Token 관련 스키마"""
from pydantic import BaseModel, Field


class CSRFTokenResponse(BaseModel):
    """CSRF 토큰 응답"""
    csrf_token: str = Field(..., description="CSRF 토큰 (X-CSRF-Token 헤더로 전송)")


class CSRFTokenRequest(BaseModel):
    """CSRF 토큰이 필요한 요청 (데코레이터에서 사용)"""
    pass
