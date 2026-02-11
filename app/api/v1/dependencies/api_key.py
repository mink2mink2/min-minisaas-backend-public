"""API Key 검증"""
from fastapi import Header, HTTPException
from app.core.config import settings


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """
    모든 요청에 필수 - API Key 검증

    Args:
        x_api_key: X-API-Key 헤더

    Returns:
        검증된 API Key

    Raises:
        HTTPException: 유효하지 않은 API Key
    """
    if x_api_key != settings.API_SECRET_KEY:
        raise HTTPException(401, "Invalid API key")
    return x_api_key
