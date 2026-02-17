"""공통 인증 엔드포인트 (플랫폼 무관)"""
from typing import Optional
from fastapi import APIRouter, Depends, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import AuthResult, CSRFTokenManager, get_strategy
from app.api.v1.dependencies.api_key import verify_api_key
from app.api.v1.dependencies.auth import verify_any_platform
from app.core.database import get_db
from app.domain.auth.services.auth_service import AuthService
from app.domain.auth.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth - Common"])


@router.post(
    "/heartbeat",
    summary="세션/토큰 유효성 확인",
    description="""
    - Web: 쿠키 세션 슬라이딩 윈도우 갱신
    - Mobile: Firebase JWT 검증만 수행
    - Desktop/Device: 자체 JWT 검증만 수행

    필수 헤더:
    - X-API-Key
    - X-Platform: web | mobile | desktop | device
    - Authorization: Bearer <token> (web 제외)
    - Cookie: session=<id> (web 전용)
    """,
)
async def heartbeat(
    request: Request,
    api_key: str = Depends(verify_api_key),
    auth: AuthResult = Depends(verify_any_platform),
) -> dict:
    """
    세션/토큰 유효성 확인

    - Web: 쿠키 세션 슬라이딩 윈도우 갱신
    - Mobile: Firebase JWT 검증만
    - Desktop/Device: JWT 검증만
    """
    strategy = get_strategy(auth.platform)
    result = await strategy.heartbeat(request)
    return {"success": True, **result}


@router.post(
    "/refresh",
    summary="토큰/세션 갱신",
    description="""
    - Web: heartbeat와 동일 (세션 기반)
    - Desktop: Refresh Token Rotation 처리
    - IoT: Refresh Token 갱신 (Rotation 없음)

    필수 헤더:
    - X-API-Key, X-Platform
    """,
)
async def refresh(
    request: Request,
    api_key: str = Depends(verify_api_key),
    auth: AuthResult = Depends(verify_any_platform),
) -> dict:
    """
    토큰/세션 갱신

    - Web: heartbeat와 동일 (세션 기반)
    - Desktop: Refresh Token Rotation
    - IoT: Refresh Token 갱신
    """
    strategy = get_strategy(auth.platform)
    result = await strategy.refresh(request)
    return {"success": True, **result}


@router.post(
    "/logout",
    summary="로그아웃 (CSRF 토큰 권장, 선택적)",
    description="""
    - Web: 서버 세션 파괴 + JWT 무효화
    - Mobile: 클라이언트 토큰 삭제를 권장
    - Desktop: Refresh Token 무효화
    - IoT: 디바이스 세션 삭제

    필수 헤더:
    - X-API-Key, X-Platform
    - Authorization: Bearer <token> 또는 Cookie: session=<id>
    - X-CSRF-Token (권장하지만 선택적 - 있으면 검증)
    """,
)
async def logout(
    request: Request,
    api_key: str = Depends(verify_api_key),
    auth: AuthResult = Depends(verify_any_platform),
) -> dict:
    """
    로그아웃 (CSRF 토큰 권장, 선택적)
    """
    # 인증된 사용자 정보
    x_platform = auth.platform
    auth_result = auth

    # CSRF 토큰 검증 (선택적 - 있으면 검증, 없으면 경고만)
    x_csrf_token = request.headers.get("X-CSRF-Token")
    if x_csrf_token:
        is_valid = await CSRFTokenManager.consume(auth_result.user_id, x_platform, x_csrf_token)
        if not is_valid:
            from fastapi import HTTPException
            raise HTTPException(403, "Invalid or expired CSRF token")
    else:
        # CSRF 토큰이 없음 - 경고만 로깅하고 진행
        import logging
        logging.warning(f"Logout without CSRF token for user {auth_result.user_id} (platform: {x_platform})")

    # 로그아웃 처리
    await strategy.logout(request, auth_result.user_id)

    # 모든 CSRF 토큰 무효화
    await CSRFTokenManager.revoke_all(auth_result.user_id)

    return {"success": True, "message": "로그아웃 완료"}


@router.get(
    "/me",
    summary="현재 사용자 정보 조회 + CSRF 토큰 발급",
    description="""
    - 모든 플랫폼에서 사용 가능
    - 민감 작업 전 호출하여 `csrf_token`을 획득하세요 (logout, account deletion)

    필수 헤더:
    - X-API-Key, X-Platform
    - Authorization 또는 Cookie (플랫폼별)
    """,
)
async def get_current_user(
    request: Request,
    api_key: str = Depends(verify_api_key),
    auth: AuthResult = Depends(verify_any_platform),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    현재 사용자 정보 조회

    모든 플랫폼에서 사용 가능
    CSRF 토큰 생성 후 응답에 포함 (logout, account deletion 전에 호출 필수)
    """
    service = AuthService(db)
    user = await service.get_user_by_id(auth.user_id)

    if not user:
        from fastapi import HTTPException

        raise HTTPException(404, "User not found")

    # CSRF 토큰 생성 (민감한 작업용)
    csrf_token = await CSRFTokenManager.create_and_store(
        user_id=auth.user_id,
        platform=auth.platform
    )

    return {
        "success": True,
        "user": UserResponse.model_validate(user).model_dump(mode='json'),
        "csrf_token": csrf_token,
    }


@router.delete(
    "/account",
    summary="계정 삭제 (소프트 삭제) - CSRF 필요",
    description="""
    - 모든 세션/토큰 무효화 후 계정 비활성화

    필수 헤더:
    - X-API-Key, X-Platform, X-CSRF-Token
    - Authorization 또는 Cookie (플랫폼별)
    """,
)
async def delete_account(
    request: Request,
    api_key: str = Depends(verify_api_key),
    auth: AuthResult = Depends(verify_any_platform),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    계정 삭제 (소프트 삭제) - CSRF 토큰 필수

    - 모든 세션/토큰 무효화
    - 사용자 계정 비활성화

    Headers:
        X-CSRF-Token: CSRF 토큰 (GET /auth/me에서 획득)
    """
    # CSRF 토큰 검증
    x_csrf_token = request.headers.get("X-CSRF-Token")
    if not x_csrf_token:
        from fastapi import HTTPException
        raise HTTPException(403, "Missing X-CSRF-Token header")

    is_valid = await CSRFTokenManager.consume(auth.user_id, auth.platform, x_csrf_token)
    if not is_valid:
        from fastapi import HTTPException
        raise HTTPException(403, "Invalid or expired CSRF token")

    # 1. 사용자 비활성화
    service = AuthService(db)
    await service.deactivate_user(auth.user_id)

    # 2. 로그아웃 처리 (모든 세션/토큰 무효화)
    strategy = get_strategy(auth.platform)
    await strategy.logout(request, auth.user_id)

    # 3. 모든 CSRF 토큰 무효화
    await CSRFTokenManager.revoke_all(auth.user_id)

    return {"success": True, "message": "계정 삭제 완료"}
