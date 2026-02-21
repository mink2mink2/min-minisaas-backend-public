"""네이버 소셜 로그인 엔드포인트"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth.naver_verifier import naver_verifier
from app.domain.auth.services.auth_service import AuthService
from app.core.database import get_db
from app.api.v1.dependencies.api_key import verify_api_key
from app.domain.auth.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth - Naver"])


class NaverLoginRequest(BaseModel):
    """네이버 로그인 요청"""
    naver_access_token: str


class NaverLoginResponse(BaseModel):
    """네이버 로그인 응답"""
    success: bool
    message: str
    user: dict
    is_new_user: bool
    expires: int = 0


@router.post(
    "/login/naver",
    summary="네이버 로그인 (네이버 액세스 토큰 → 서버 상태)",
    description="""
    필수 헤더:
    - X-API-Key

    요청 Body:
    - naver_access_token: 네이버에서 발급받은 액세스 토큰

    동작:
    - 네이버 REST API로 토큰 검증 및 사용자 정보 조회
    - 신규/기존 사용자 자동 생성/업데이트
    - 응답: 사용자 정보 + 메타데이터
    """,
)
async def login_naver(
    request_data: NaverLoginRequest,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> NaverLoginResponse:
    """
    네이버 로그인 엔드포인트

    - 네이버 액세스 토큰 검증
    - 사용자 정보 조회
    - 신규/기존 사용자 자동 생성/업데이트
    """

    # 1. 네이버 토큰 검증 및 사용자 정보 조회
    try:
        user_info = await naver_verifier.verify(request_data.naver_access_token)
    except HTTPException:
        raise

    # 2. 비즈니스 로직 (유저 조회/생성 - 공통)
    service = AuthService(db)
    user, is_new = await service.get_or_create_user(
        user_id=user_info["user_id"],
        email=user_info.get("email"),
        name=user_info.get("nickname"),
        picture=user_info.get("picture"),
    )

    # 3. 응답 생성
    return NaverLoginResponse(
        success=True,
        message="가입 완료! 10포인트 지급" if is_new else "로그인 성공",
        user=UserResponse.model_validate(user).model_dump(mode='json'),
        is_new_user=is_new,
        expires=0,  # Stateless - 만료 없음
    )
