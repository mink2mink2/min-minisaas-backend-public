"""인증 엔드포인트"""
from fastapi import APIRouter

# Import all routers
from app.api.v1.endpoints.auth.legacy import router as legacy_router
from app.api.v1.endpoints.auth.web import router as web_router
from app.api.v1.endpoints.auth.mobile import router as mobile_router
from app.api.v1.endpoints.auth.desktop import router as desktop_router
from app.api.v1.endpoints.auth.device import router as device_router
from app.api.v1.endpoints.auth.common import router as common_router
from app.api.v1.endpoints.auth.kakao import router as kakao_router
from app.api.v1.endpoints.auth.naver import router as naver_router

# Combine all routers
router = APIRouter()
router.include_router(legacy_router)  # Legacy email+password endpoints
router.include_router(web_router)  # Web (Firebase → Server Session)
router.include_router(mobile_router)  # Mobile (Firebase → Stateless JWT)
router.include_router(desktop_router)  # Desktop (OAuth2 PKCE)
router.include_router(device_router)  # Device/IoT (API Key + Secret)
router.include_router(kakao_router)  # Kakao (Kakao OAuth)
router.include_router(naver_router)  # Naver (Naver OAuth)
router.include_router(common_router)  # Common endpoints (logout, me, heartbeat, etc.)

__all__ = ["router"]
