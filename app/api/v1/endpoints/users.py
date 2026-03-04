"""
User endpoints
Profile management, settings, search
"""
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import verify_api_key
from app.api.v1.dependencies.auth import AuthResult, verify_any_platform
from app.core.database import get_db
from app.core.security import get_current_user
from app.domain.auth.services.auth_service import AuthService
from app.domain.auth.models.user import User
from app.domain.auth.schemas.user import UserResponse, UserUpdate

router = APIRouter()


@router.get("/search")
async def search_users(
    q: str = Query(..., min_length=2, max_length=100, description="검색어 (사용자명 또는 이메일)"),
    limit: int = Query(10, ge=1, le=100),
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    사용자 검색 API

    - Query parameter로 사용자명 또는 이메일 검색
    - 자신을 제외한 다른 사용자만 반환
    - Rate limit: 10req/sec
    - Response: [{ id, name, picture, username, email }]
    """
    try:
        service = AuthService(db)
        users = await service.search_users(
            query=q,
            exclude_user_id=auth.user_id,
            limit=limit
        )
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """현재 사용자 프로필 조회"""
    result = await db.execute(select(User).where(User.id == UUID(auth.user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    data: UserUpdate,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    현재 사용자 프로필 업데이트

    - nickname: 게시글/댓글에 표시될 이름
    - name: 실명
    - picture: 프로필 사진 URL
    """
    user_id = UUID(auth.user_id)

    # 업데이트할 필드만 준비
    update_data = {}
    if data.nickname is not None:
        update_data["nickname"] = data.nickname
    if data.name is not None:
        update_data["name"] = data.name
    if data.picture is not None:
        update_data["picture"] = data.picture

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # 업데이트 실행
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(**update_data)
    )
    await db.commit()

    # 업데이트된 사용자 정보 반환
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    return user


@router.get("/{user_id}")
async def get_user_profile(user_id: str):
    """Get user profile by ID"""
    # TODO: Fetch user from database
    return {"user_id": user_id}
