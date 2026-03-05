"""API v1 라우터"""
from fastapi import APIRouter
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.board import board_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.blog import router as blog_router
from app.api.v1.endpoints.pdf import pdf_router
from app.api.v1.endpoints.points import router as points_router
from app.api.v1.endpoints.ledger import router as ledger_router
from app.api.v1.endpoints.push import router as push_router
from app.api.v1.endpoints.users import router as users_router

api_router = APIRouter()

# Auth endpoints (includes legacy email+password and new platform-specific endpoints)
api_router.include_router(auth_router)

# Users endpoints (profile management, search)
api_router.include_router(users_router, prefix="/users", tags=["users"])

# Board endpoints (posts, comments, likes, bookmarks)
api_router.include_router(board_router)

# Chat endpoints (rooms, messages, websocket)
api_router.include_router(chat_router)

# Blog endpoints (posts, feed, likes, subscriptions)
api_router.include_router(blog_router)

# PDF endpoints (file upload, conversion, status)
api_router.include_router(pdf_router)

# Points endpoints (balance, charge, consume, history)
api_router.include_router(points_router)

# Ledger endpoints (verification, integrity check)
api_router.include_router(ledger_router)

# Push notification endpoints (tokens, notifications)
api_router.include_router(push_router)
