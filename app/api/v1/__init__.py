"""API v1 라우터"""
from fastapi import APIRouter
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.board import board_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.pdf import pdf_router
from app.api.v1.endpoints.points import router as points_router
from app.api.v1.endpoints.ledger import router as ledger_router

api_router = APIRouter()

# Auth endpoints (includes legacy email+password and new platform-specific endpoints)
api_router.include_router(auth_router)

# Board endpoints (posts, comments, likes, bookmarks)
api_router.include_router(board_router)

# Chat endpoints (rooms, messages, websocket)
api_router.include_router(chat_router)

# PDF endpoints (file upload, conversion, status)
api_router.include_router(pdf_router)

# Points endpoints (balance, charge, consume, history)
api_router.include_router(points_router)

# Ledger endpoints (verification, integrity check)
api_router.include_router(ledger_router)
