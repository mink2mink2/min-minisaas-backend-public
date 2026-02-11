"""인증 의존성"""
from typing import Optional
from fastapi import Request, Header, HTTPException
from app.auth.base import AuthResult
from app.auth.firebase_verifier import firebase_verifier
from app.auth.session_manager import session_manager
from app.auth.jwt_manager import jwt_manager
from app.core.security import decode_token


def _extract_bearer_token(authorization: str) -> str:
    """Bearer 토큰 추출"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    return authorization[7:]


async def verify_web_session(request: Request) -> AuthResult:
    """
    Web 전용 - 쿠키 세션 검증

    Args:
        request: FastAPI Request

    Returns:
        AuthResult

    Raises:
        HTTPException: 세션 검증 실패
    """
    session_id = request.cookies.get("session")
    if not session_id:
        raise HTTPException(401, "No session cookie")

    session_data = await session_manager.validate_and_slide(session_id)
    if not session_data:
        raise HTTPException(401, "Session expired or invalid")

    return AuthResult(
        user_id=session_data["user_id"],
        platform="web",
        auth_type="session",
        expires=int(session_data["expires"]),
    )


async def verify_firebase_jwt(authorization: str = Header(...)) -> AuthResult:
    """
    Mobile 전용 - Firebase JWT 검증

    Args:
        authorization: Authorization 헤더

    Returns:
        AuthResult

    Raises:
        HTTPException: JWT 검증 실패
    """
    token = _extract_bearer_token(authorization)

    # Firebase JWT 검증
    payload = await firebase_verifier.verify(token)

    return AuthResult(
        user_id=payload.get("sub"),
        email=payload.get("email"),
        name=payload.get("name"),
        picture=payload.get("picture"),
        platform="mobile",
        auth_type="firebase",
        expires=payload.get("exp"),
    )


async def verify_self_jwt(authorization: str = Header(...)) -> AuthResult:
    """
    Desktop/IoT 전용 - 자체 발급 JWT 검증

    Args:
        authorization: Authorization 헤더

    Returns:
        AuthResult

    Raises:
        HTTPException: JWT 검증 실패
    """
    token = _extract_bearer_token(authorization)

    try:
        payload = decode_token(token)
    except Exception as e:
        raise HTTPException(401, f"Invalid JWT: {str(e)}")

    return AuthResult(
        user_id=payload.get("sub"),
        platform=payload.get("platform", "desktop"),
        auth_type="self_jwt",
        expires=payload.get("exp"),
    )


async def verify_any_platform(
    request: Request,
    x_platform: str = Header(..., alias="X-Platform"),
    authorization: Optional[str] = Header(None),
) -> AuthResult:
    """
    공통 엔드포인트용 - X-Platform 헤더로 분기

    /auth/me, /auth/logout, /auth/account 등에서 사용

    Args:
        request: FastAPI Request
        x_platform: X-Platform 헤더 ("web" | "mobile" | "desktop" | "device")
        authorization: Authorization 헤더

    Returns:
        AuthResult

    Raises:
        HTTPException: 인증 검증 실패
    """
    if x_platform == "web":
        return await verify_web_session(request)
    elif x_platform == "mobile":
        return await verify_firebase_jwt(authorization=authorization or "")
    elif x_platform in ("desktop", "device"):
        return await verify_self_jwt(authorization=authorization or "")
    else:
        raise HTTPException(400, f"Unknown platform: {x_platform}")
