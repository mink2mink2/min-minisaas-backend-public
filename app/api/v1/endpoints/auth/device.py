"""IoT Device 플랫폼 인증 엔드포인트"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from app.domain.auth.models.device import Device
from app.core.database import get_db
from app.api.v1.dependencies.api_key import verify_api_key
from app.core.cache import cache
from app.core.exceptions import AuthException
from datetime import datetime
import secrets

router = APIRouter(prefix="/auth", tags=["Auth - Device"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Rate limiting constants
DEVICE_FAILED_LOGIN_LIMIT = 5
DEVICE_LOCKOUT_MINUTES = 15


@router.post(
    "/login/device",
    summary="IoT 디바이스 로그인 (API Key + Device Secret)",
    description="""
    필수 헤더:
    - X-API-Key

    요청 바디:
    - device_id: 디바이스 ID
    - device_secret: 디바이스 시크릿
    """,
)
async def login_device(
    request: Request,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    IoT Device 로그인 엔드포인트

    Request Body:
        - device_id: 디바이스 ID
        - device_secret: 디바이스 시크릿
    """
    from app.core.auth import get_strategy, AuthResult

    try:
        body = await request.json()
        device_id = body.get("device_id")
        device_secret = body.get("device_secret")

        if not device_id or not device_secret:
            raise AuthException("MISSING_FIELD", 400)

        # 🔴 Step 1: Rate Limiting - 기기가 잠금 상태인지 확인
        lockout_key = f"device:locked:{device_id}"
        is_locked = await cache.get(lockout_key)
        if is_locked:
            raise AuthException("DEVICE_LOCKED", 429)

        # DB에서 디바이스 조회
        result = await db.execute(
            select(Device).where(Device.device_id == device_id)
        )
        device = result.scalar_one_or_none()

        if not device:
            raise AuthException("DEVICE_NOT_FOUND", 401)

        if not device.is_active:
            raise AuthException("DEVICE_INACTIVE", 401)

        # 🔴 Step 2: 실패 시도 추적 및 검증
        failed_login_key = f"device:failed_login:{device_id}"

        # 디바이스 시크릿 검증
        if not pwd_context.verify(device_secret, device.device_secret_hash):
            # 실패 카운터 증가
            failed_count = await cache.incr(failed_login_key)

            # TTL 설정 (첫 시도에만)
            if failed_count == 1:
                await cache.set(failed_login_key, failed_count, ttl_seconds=3600)

            # 실패 횟수가 제한을 초과하면 기기 잠금
            if failed_count >= DEVICE_FAILED_LOGIN_LIMIT:
                await cache.set(
                    lockout_key,
                    "locked",
                    ttl_seconds=DEVICE_LOCKOUT_MINUTES * 60
                )
                raise AuthException("DEVICE_LOCKED", 429)

            raise AuthException("INVALID_CREDENTIALS", 401)

        # 🔴 Step 3: 성공 - 실패 카운터 초기화
        await cache.delete(failed_login_key)

        # AuthResult 생성
        auth_result = AuthResult(
            user_id=str(device.owner_id),
            platform="device",
            auth_type="api_key",
            expires=int(__import__("time").time()) + (30 * 86400),  # 30일
            metadata={"device_id": device_id},
        )

        # 전략 실행
        strategy = get_strategy("device")

        # 1. 세션/토큰 생성
        session_data = await strategy.create_session(auth_result)

        # 2. 응답 생성
        response_data = {
            "success": True,
            "device_id": device_id,
            "owner_id": str(device.owner_id),
            "message": "디바이스 로그인 성공",
        }
        return await strategy.build_response(response_data, session_data)

    except AuthException:
        raise
    except Exception as e:
        raise AuthException("SERVER_ERROR", 500)


@router.post(
    "/refresh/device",
    summary="IoT 디바이스 토큰 갱신",
    description="""
    필수 헤더:
    - X-API-Key

    요청 바디:
    - refresh_token: 현재 refresh token (Rotation 미적용)
    """,
)
async def refresh_device(
    request: Request,
    api_key: str = Depends(verify_api_key),
):
    """
    IoT Device 토큰 갱신 엔드포인트

    Request Body:
        - refresh_token: 현재 refresh token
    """
    from app.core.auth import get_strategy

    strategy = get_strategy("device")
    result = await strategy.refresh(request)
    return {"success": True, **result}


@router.post(
    "/device/{device_id}/rotate-secret",
    summary="IoT 디바이스 시크릿 로테이션",
    description="""
    기존 시크릿으로 검증 후 새로운 시크릿을 발급합니다. 발급된 시크릿은 한 번만 응답에 표시됩니다.

    필수 헤더:
    - X-API-Key

    요청 바디:
    - device_secret: 현재 디바이스 시크릿 (검증용)
    """,
)
async def rotate_device_secret(
    device_id: str,
    request: Request,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    IoT Device 시크릿 로테이션 엔드포인트

    기존 시크릿으로 검증 후 새로운 시크릿을 생성하여 반환

    Request Body:
        - device_secret: 현재 디바이스 시크릿 (검증용)

    Response:
        - success: true
        - device_id: 디바이스 ID
        - new_secret: 새로운 시크릿 (한 번만 표시)
        - message: 안내 메시지
    """
    try:
        body = await request.json()
        old_secret = body.get("device_secret")

        if not old_secret:
            raise AuthException("MISSING_FIELD", 400)

        # DB에서 디바이스 조회
        result = await db.execute(
            select(Device).where(Device.device_id == device_id)
        )
        device = result.scalar_one_or_none()

        if not device:
            raise AuthException("DEVICE_NOT_FOUND", 404)

        if not device.is_active:
            raise AuthException("DEVICE_INACTIVE", 401)

        # 🔴 Step 1: 기존 시크릿 검증
        if not pwd_context.verify(old_secret, device.device_secret_hash):
            raise AuthException("INVALID_CREDENTIALS", 401)

        # 🔴 Step 2: 새 시크릿 생성
        new_secret = secrets.token_urlsafe(32)
        new_hash = pwd_context.hash(new_secret)

        # 🔴 Step 3: 새 해시를 DB에 저장
        device.device_secret_hash = new_hash
        device.secret_rotated_at = datetime.utcnow()
        await db.commit()

        # 🔴 Step 4: SecurityLog 기록
        from app.domain.auth.models.security_log import SecurityLog
        from app.core.events import event_bus, SecurityAlertEvent

        log = SecurityLog(
            user_id=str(device.owner_id),
            event_type="DEVICE_SECRET_ROTATED",
            device_id=device_id,
            details={
                "device_name": device.name,
                "rotation_time": device.secret_rotated_at.isoformat() if device.secret_rotated_at else None,
            },
        )
        db.add(log)
        await db.commit()

        # 보안 경고 이벤트 발행 (이벤트 기반 알림)
        try:
            await event_bus.emit(SecurityAlertEvent(
                user_id=str(device.owner_id),
                event_type="DEVICE_SECRET_ROTATED",
                severity="MEDIUM",
                details={
                    "device_id": device_id,
                    "device_name": device.name,
                },
                device_id=device_id
            ))
        except Exception:
            pass

        return {
            "success": True,
            "device_id": device_id,
            "new_secret": new_secret,  # Only shown once!
            "message": "Secret rotated successfully. Save the new secret securely.",
        }

    except AuthException:
        raise
    except Exception as e:
        raise AuthException("SERVER_ERROR", 500)
