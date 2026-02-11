"""API 엔드포인트"""
from fastapi import APIRouter
from app.api.v1.endpoints.auth import router as auth_router

__all__ = ["auth_router"]
