"""인증 의존성"""
from typing import Optional
from fastapi import Request, Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import AuthResult, CSRFTokenManager
from app.core.auth.firebase_verifier import firebase_verifier
from app.core.auth.session_manager import session_manager
from app.core.security import decode_token
from app.core.database import get_db


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
    import logging
    logger = logging.getLogger(__name__)

    logger.info("🔍 === verify_web_session 시작 ===")
    logger.info(f"🔍 Request URL: {request.url}")
    logger.info(f"🔍 Cookie keys: {list(request.cookies.keys())}")
    logger.info(f"🔍 Header keys: {list(request.headers.keys())}")

    session_id = request.cookies.get("session")
    logger.info(f"🔍 session cookie present: {session_id is not None}")

    if not session_id:
        logger.error("❌ No session cookie found!")
        logger.error(f"❌ request.cookies keys: {list(request.cookies.keys())}")
        raise HTTPException(401, "No session cookie")

    session_data = await session_manager.validate_and_slide(session_id)
    logger.info(f"🔍 session_data found: {session_data is not None}")

    if not session_data:
        logger.error(f"❌ Session not found in Redis for session_id: {session_id}")
        raise HTTPException(401, "Session expired or invalid")

    logger.info(f"✅ Session validated for user: {session_data['user_id']}")

    return AuthResult(
        user_id=session_data["user_id"],
        platform="web",
        auth_type="session",
        expires=int(session_data["expires"]),
    )


async def verify_firebase_jwt(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> AuthResult:
    """
    Mobile 전용 - Firebase JWT 검증 (firebase_uid → DB user UUID 변환)

    Args:
        authorization: Authorization 헤더
        db: AsyncSession

    Returns:
        AuthResult

    Raises:
        HTTPException: JWT 검증 실패
    """
    token = _extract_bearer_token(authorization)

    # Firebase JWT 검증
    payload = await firebase_verifier.verify(token)
    firebase_uid = payload.get("sub")

    # Convert firebase_uid to DB user UUID
    from sqlalchemy import select
    from app.domain.auth.models.user import User

    result = await db.execute(
        select(User.id).where(User.firebase_uid == firebase_uid)
    )
    db_user_id = result.scalar_one_or_none()

    if not db_user_id:
        # User not found - return firebase_uid anyway (will create during login)
        user_id = firebase_uid
    else:
        user_id = str(db_user_id)

    return AuthResult(
        user_id=user_id,
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
    db: AsyncSession = Depends(get_db),
) -> AuthResult:
    """
    공통 엔드포인트용 - X-Platform 헤더로 분기

    /auth/me, /auth/logout, /auth/account 등에서 사용

    Args:
        request: FastAPI Request
        x_platform: X-Platform 헤더 ("web" | "mobile" | "desktop" | "device")
        authorization: Authorization 헤더
        db: AsyncSession

    Returns:
        AuthResult

    Raises:
        HTTPException: 인증 검증 실패
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.debug(f"=== verify_any_platform 시작 ===")
    logger.debug(f"X-Platform: {x_platform}")
    logger.debug(f"Authorization header present: {authorization is not None}")
    logger.debug(f"Request URL: {request.url}")

    if x_platform == "web":
        logger.debug(f"Platform is 'web' - calling verify_web_session")
        return await verify_web_session(request)
    elif x_platform == "mobile":
        logger.debug(f"Platform is 'mobile' - calling verify_firebase_jwt")
        return await verify_firebase_jwt(authorization=authorization or "", db=db)
    elif x_platform in ("desktop", "device"):
        logger.debug(f"Platform is '{x_platform}' - calling verify_self_jwt")
        return await verify_self_jwt(authorization=authorization or "")
    else:
        logger.error(f"Unknown platform: {x_platform}")
        raise HTTPException(400, f"Unknown platform: {x_platform}")


async def verify_csrf_token(
    user_id: str,
    platform: str,
    x_csrf_token: str = Header(None, alias="X-CSRF-Token"),
) -> str:
    """
    CSRF 토큰 검증 - 민감한 작업 (logout, delete account)에서 사용

    Args:
        user_id: 사용자 ID
        platform: 플랫폼
        x_csrf_token: X-CSRF-Token 헤더

    Returns:
        유효한 CSRF 토큰

    Raises:
        HTTPException: CSRF 토큰 검증 실패
    """
    if not x_csrf_token:
        raise HTTPException(403, "Missing X-CSRF-Token header")

    # 토큰 검증 및 소비 (1회용)
    is_valid = await CSRFTokenManager.consume(user_id, platform, x_csrf_token)

    if not is_valid:
        raise HTTPException(403, "Invalid or expired CSRF token")

    return x_csrf_token
