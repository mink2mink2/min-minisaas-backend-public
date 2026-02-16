"""
User endpoints
Profile management, settings, search
"""
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import verify_api_key
from app.api.v1.dependencies.auth import AuthResult, verify_any_platform
from app.core.database import get_db
from app.core.security import get_current_user
from app.domain.auth.services.auth_service import AuthService

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


@router.get("/me")
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    return {"user_id": current_user["id"]}


@router.put("/me")
async def update_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Update current user profile"""
    # TODO: Update user profile
    return {"message": "Profile updated"}


@router.get("/{user_id}")
async def get_user_profile(user_id: str):
    """Get user profile by ID"""
    # TODO: Fetch user from database
    return {"user_id": user_id}
