"""FastAPI 앱"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
from app.core.cache import cache
from app.core.config import settings
from app.core.exceptions import AuthException, auth_exception_handler
from app.core.events import event_bus
from app.core.fcm import initialize_firebase
from app.core.notifications.notification_service import notification_service
from app.domain.chat.services.chat_event_handlers import register_chat_event_handlers
from app.domain.pdf.services.pdf_event_handlers import register_pdf_event_handlers
from app.domain.points.services.points_event_handlers import register_points_event_handlers
from app.domain.blog.events import blog_event_handlers  # noqa: F401
from app.domain.push.events import push_event_handlers  # noqa: F401

app = FastAPI(title="min-minisaas", version="0.1.0")

# CORS - 맨 먼저 추가 (middleware는 역순으로 실행되므로 첫 번째가 마지막에 실행)
cors_origins = settings.CORS_ORIGINS
# 개발 환경에서는 localhost:* 패턴도 허용
if settings.ENVIRONMENT == "development":
    # 개발: localhost 모든 포트 허용
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://localhost:\d+|http://127\.0\.0\.1:\d+",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
        expose_headers=["X-Total-Count", "X-Page-Count"],
        max_age=600,
    )
else:
    # 프로덕션: 명시적 도메인만 허용
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
        expose_headers=["X-Total-Count", "X-Page-Count"],
        max_age=600,
    )

# Register exception handler for unified auth errors
app.add_exception_handler(AuthException, auth_exception_handler)

@app.on_event("startup")
async def startup():
    import logging
    logger = logging.getLogger(__name__)

    # 🔍 디버그: 설정 출력
    logger.info(f"🌍 ENVIRONMENT: {settings.ENVIRONMENT}")
    logger.info(f"🍪 COOKIE_SECURE: {settings.COOKIE_SECURE}")
    logger.info(f"🍪 COOKIE_SAMESITE: {settings.COOKIE_SAMESITE}")
    logger.info(f"🔐 SESSION_TTL_MIN: {settings.SESSION_TTL_MIN}")

    await cache.init()
    await event_bus.connect()

    # 이벤트 핸들러 등록
    event_bus.subscribe("security.alert", notification_service.handle_security_alert)

    # PDF 이벤트 핸들러 등록
    await register_pdf_event_handlers(event_bus)

    # 포인트 이벤트 핸들러 등록
    await register_points_event_handlers(event_bus)

    # 채팅 이벤트 핸들러 등록
    await register_chat_event_handlers(event_bus)

    # FCM 서비스 상태 확인
    if settings.FCM_CREDENTIALS_PATH:
        try:
            initialize_firebase()
            print("✓ Firebase Cloud Messaging (FCM) initialized successfully")
        except Exception:
            print("⚠ Firebase Cloud Messaging (FCM) initialization failed")
    else:
        print("⚠ Firebase Cloud Messaging (FCM) not configured")

# 라우터
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}
