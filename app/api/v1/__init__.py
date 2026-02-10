"""API v1 라우터"""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, chat, points, ledger

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(points.router, prefix="/points", tags=["points"])
api_router.include_router(ledger.router, prefix="/verify", tags=["ledger"])