"""Web 플랫폼 인증 엔드포인트"""
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import get_strategy
from app.domain.auth.services.auth_service import AuthService
from app.core.database import get_db
from app.api.v1.dependencies.api_key import verify_api_key
from app.domain.auth.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth - Web"])


@router.post(
    "/login/web",
    summary="Web 로그인 (Firebase JWT → 서버 세션)",
    description="""
    필수 헤더:
    - X-API-Key
    - Authorization: Bearer <firebase_jwt>

    동작:
    - Firebase JWT 검증 후 서버사이드 세션 생성 및 HttpOnly 쿠키 설정
    """,
)
async def login_web(
    request: Request,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Web 로그인 엔드포인트

    - Firebase JWT를 Authorization 헤더로 받음
    - 서버사이드 세션 생성 + HttpOnly Cookie 설정
    - 신규/기존 사용자 자동 생성/업데이트
    """
    # 🚫 TEMPORARILY DISABLED (2026-02-17)
    raise HTTPException(status_code=503, detail="Web login temporarily disabled for maintenance")

    import logging
    logger = logging.getLogger(__name__)

    logger.debug(f"=== login_web 시작 ===")

    strategy = get_strategy("web")

    # 1. 인증 (Firebase JWT 검증)
    auth_result = await strategy.authenticate(request)
    logger.debug(f"✅ Firebase JWT authenticated, user_id: {auth_result.user_id}")

    # 2. 비즈니스 로직 (유저 조회/생성 - 공통)
    service = AuthService(db)
    user, is_new = await service.get_or_create_user(
        user_id=auth_result.user_id,
        email=auth_result.email,
        name=auth_result.name,
        picture=auth_result.picture,
    )
    logger.debug(f"✅ User found/created: {user.id}, is_new: {is_new}")

    # Update auth_result.user_id to DB user UUID (not Firebase UID)
    auth_result.user_id = str(user.id)

    # 3. 세션 생성 (플랫폼별) - Request를 metadata에 포함
    auth_result.metadata["request"] = request
    session_data = await strategy.create_session(auth_result)
    logger.debug(f"✅ Session created: {session_data.get('session_id')}")

    # 4. 응답 생성 (플랫폼별)
    response_data = {
        "success": True,
        "message": "가입 완료! 10포인트 지급" if is_new else "로그인 성공",
        "user": UserResponse.model_validate(user).model_dump(mode='json'),
        "is_new_user": is_new,
        "expires": session_data.get("expires"),
    }
    logger.debug(f"✅ Calling build_response with session_data")
    response = await strategy.build_response(response_data, session_data)
    logger.debug(f"✅ Response built, Set-Cookie header should be set")
    return response
