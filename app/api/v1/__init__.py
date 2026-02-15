"""API v1 라우터"""
from fastapi import APIRouter
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.board import board_router
from app.api.v1.endpoints.pdf import pdf_router
# from app.api.v1.endpoints import chat, points, ledger

api_router = APIRouter()

# Auth endpoints (includes legacy email+password and new platform-specific endpoints)
api_router.include_router(auth_router)

# Board endpoints (posts, comments, likes, bookmarks)
api_router.include_router(board_router)

# PDF endpoints (file upload, conversion, status)
api_router.include_router(pdf_router)

# TODO: Uncomment when features modules are available
# api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
# api_router.include_router(points.router, prefix="/points", tags=["points"])
# api_router.include_router(ledger.router, prefix="/verify", tags=["ledger"])