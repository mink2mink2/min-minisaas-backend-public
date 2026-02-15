"""Board API endpoints"""
from fastapi import APIRouter
from app.api.v1.endpoints.board.categories import router as categories_router
from app.api.v1.endpoints.board.posts import router as posts_router
from app.api.v1.endpoints.board.comments import router as comments_router
from app.api.v1.endpoints.board.reactions import router as reactions_router

board_router = APIRouter(prefix="/board", tags=["board"])

# Include all sub-routers
board_router.include_router(categories_router, prefix="/categories")
board_router.include_router(posts_router, prefix="/posts")
board_router.include_router(comments_router, prefix="/posts")
board_router.include_router(reactions_router)

__all__ = ["board_router"]
