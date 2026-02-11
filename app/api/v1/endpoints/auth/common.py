"""공통 인증 엔드포인트 (플랫폼 무관)"""
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.base import AuthResult
from app.api.v1.dependencies.api_key import verify_api_key
from app.api.v1.dependencies.auth import verify_any_platform
from app.core.database import get_db
from app.services.auth_service import AuthService
from app.auth import get_strategy
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth - Common"])


@router.post("/heartbeat")
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


@router.post("/refresh")
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


@router.post("/logout")
async def logout(
    request: Request,
    api_key: str = Depends(verify_api_key),
    auth: AuthResult = Depends(verify_any_platform),
) -> dict:
    """
    로그아웃

    - Web: 서버 세션 파괴 + JWT 무효화
    - Mobile: JWT 무효화 (클라이언트가 토큰 삭제)
    - Desktop: Refresh Token 무효화
    - IoT: 디바이스 세션 삭제
    """
    strategy = get_strategy(auth.platform)
    await strategy.logout(request, auth.user_id)
    return {"success": True, "message": "로그아웃 완료"}


@router.get("/me")
async def get_current_user(
    request: Request,
    api_key: str = Depends(verify_api_key),
    auth: AuthResult = Depends(verify_any_platform),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    현재 사용자 정보 조회

    모든 플랫폼에서 사용 가능
    """
    service = AuthService(db)
    user = await service.get_user_by_id(auth.user_id)

    if not user:
        from fastapi import HTTPException

        raise HTTPException(404, "User not found")

    return {
        "success": True,
        "user": UserResponse.model_validate(user).model_dump(),
    }


@router.delete("/account")
async def delete_account(
    request: Request,
    api_key: str = Depends(verify_api_key),
    auth: AuthResult = Depends(verify_any_platform),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    계정 삭제 (소프트 삭제)

    - 모든 세션/토큰 무효화
    - 사용자 계정 비활성화
    """
    service = AuthService(db)

    # 1. 사용자 비활성화
    await service.deactivate_user(auth.user_id)

    # 2. 로그아웃 처리 (모든 세션/토큰 무효화)
    strategy = get_strategy(auth.platform)
    await strategy.logout(request, auth.user_id)

    return {"success": True, "message": "계정 삭제 완료"}
