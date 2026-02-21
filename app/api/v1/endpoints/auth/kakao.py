"""Kakao OAuth 로그인 엔드포인트"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import get_strategy
from app.domain.auth.services.auth_service import AuthService
from app.core.database import get_db
from app.api.v1.dependencies.api_key import verify_api_key
from app.domain.auth.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth - Kakao"])


@router.post(
    "/login/kakao",
    summary="Kakao 로그인 (Kakao OAuth)",
    description="""
    필수 헤더:
    - X-API-Key

    요청 Body:
    {
      "kakao_access_token": "Kakao에서 발급받은 액세스 토큰"
    }

    동작:
    - Kakao REST API로 토큰 검증 및 사용자 정보 조회
    - 신규/기존 사용자 자동 생성/업데이트
    - Stateless 응답 (토큰 없음, 쿠키 없음)
    """,
)
async def login_kakao(
    request: Request,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Kakao OAuth 로그인 엔드포인트
    
    - Kakao 액세스 토큰 검증
    - 사용자 정보 조회
    - 신규/기존 사용자 자동 생성/업데이트
    """
    strategy = get_strategy("kakao")

    # 1. 인증 (Kakao 토큰 검증)
    auth_result = await strategy.authenticate(request)

    # 2. 비즈니스 로직 (유저 조회/생성 - 공통)
    service = AuthService(db)
    user, is_new = await service.get_or_create_user(
        user_id=auth_result.user_id,
        email=auth_result.email,
        name=auth_result.name,
        picture=auth_result.picture,
    )

    # 3. 세션 생성 (플랫폼별 - Kakao는 stateless)
    session_data = await strategy.create_session(auth_result)

    # 4. 응답 생성 (플랫폼별)
    response_data = {
        "success": True,
        "message": "가입 완료! 10포인트 지급" if is_new else "로그인 성공",
        "user": UserResponse.model_validate(user).model_dump(mode='json'),
        "is_new_user": is_new,
        "expires": session_data.get("expires"),
    }
    return await strategy.build_response(response_data, session_data)
