"""Desktop 플랫폼 인증 엔드포인트"""
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import get_strategy
from app.domain.auth.services.auth_service import AuthService
from app.core.database import get_db
from app.api.v1.dependencies.api_key import verify_api_key

router = APIRouter(prefix="/auth", tags=["Auth - Desktop"])


@router.post(
    "/login/desktop",
    summary="Desktop 로그인 (OAuth2 PKCE → 자체 JWT)",
    description="""
    필수 헤더:
    - X-API-Key

    요청 바디:
    - code: Google authorization code
    - code_verifier: PKCE code verifier
    - device_id: 선택적 기기 식별자
    """,
)
async def login_desktop(
    request: Request,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Desktop 로그인 엔드포인트 (OAuth2 PKCE)

    Request Body:
        - code: Google authorization code
        - code_verifier: PKCE code verifier
        - device_id: Optional device identifier
    """
    # 🚫 TEMPORARILY DISABLED (2026-02-17)
    raise HTTPException(status_code=503, detail="Desktop login temporarily disabled for maintenance")

    strategy = get_strategy("desktop")

    # 1. 인증 (OAuth2 PKCE → Google Token Exchange)
    auth_result = await strategy.authenticate(request)

    # 2. 비즈니스 로직 (유저 조회/생성 - 공통)
    service = AuthService(db)
    user, is_new = await service.get_or_create_user(
        user_id=auth_result.user_id,
        email=auth_result.email,
        name=auth_result.name,
        picture=auth_result.picture,
    )

    # Update auth_result.user_id to DB user UUID (not Google OAuth ID)
    auth_result.user_id = str(user.id)

    # 3. 세션/토큰 생성 (플랫폼별)
    session_data = await strategy.create_session(auth_result)

    # 4. 응답 생성 (플랫폼별)
    response_data = {
        "success": True,
        "message": "가입 완료! 10포인트 지급" if is_new else "로그인 성공",
        "user": AuthService.serialize_user_response(user),
        "is_new_user": is_new,
    }
    return await strategy.build_response(response_data, session_data)


@router.post(
    "/refresh/desktop",
    summary="Desktop 토큰 갱신 (Refresh Rotation)",
    description="""
    필수 헤더:
    - X-API-Key

    요청 바디:
    - refresh_token: 현재 리프레시 토큰
    """,
)
async def refresh_desktop(
    request: Request,
    api_key: str = Depends(verify_api_key),
):
    """
    Desktop 토큰 갱신 엔드포인트 (Refresh Token Rotation)

    Request Body:
        - refresh_token: Current refresh token
    """
    strategy = get_strategy("desktop")
    result = await strategy.refresh(request)
    return {"success": True, **result}
