"""
User endpoints
Profile management, settings
"""
from fastapi import APIRouter, Depends

from app.core.security import get_current_user

router = APIRouter()


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
