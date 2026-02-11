"""Mobile 플랫폼 인증 엔드포인트"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import get_strategy
from app.domain.auth.services.auth_service import AuthService
from app.core.database import get_db
from app.api.v1.dependencies.api_key import verify_api_key
from app.domain.auth.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth - Mobile"])


@router.post(
    "/login/mobile",
    summary="Mobile 로그인 (Firebase JWT, Stateless)",
    description="""
    필수 헤더:
    - X-API-Key
    - Authorization: Bearer <firebase_jwt>

    동작:
    - Firebase JWT 검증 후 Stateless로 동작 (서버 세션 없음)
    """,
)
async def login_mobile(
    request: Request,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Mobile 로그인 엔드포인트

    - Firebase JWT를 Authorization 헤더로 받음
    - Stateless 인증 (서버세션 없음, 클라이언트가 JWT 보관)
    - 신규/기존 사용자 자동 생성/업데이트
    """
    strategy = get_strategy("mobile")

    # 1. 인증 (Firebase JWT 검증)
    auth_result = await strategy.authenticate(request)

    # 2. 비즈니스 로직 (유저 조회/생성 - 공통)
    service = AuthService(db)
    user, is_new = await service.get_or_create_user(
        user_id=auth_result.user_id,
        email=auth_result.email,
        name=auth_result.name,
        picture=auth_result.picture,
    )

    # 3. 세션 생성 (플랫폼별 - Mobile은 stateless)
    session_data = await strategy.create_session(auth_result)

    # 4. 응답 생성 (플랫폼별)
    response_data = {
        "success": True,
        "message": "가입 완료! 10포인트 지급" if is_new else "로그인 성공",
        "user": UserResponse.model_validate(user).model_dump(),
        "is_new_user": is_new,
        "expires": session_data.get("expires"),
    }
    return await strategy.build_response(response_data, session_data)
