"""IoT Device 플랫폼 인증 엔드포인트"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from app.models.device import Device
from app.core.database import get_db
from app.api.v1.dependencies.api_key import verify_api_key
from fastapi import HTTPException

router = APIRouter(prefix="/auth", tags=["Auth - Device"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/login/device")
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
    from app.auth import get_strategy
    from app.auth.base import AuthResult

    try:
        body = await request.json()
        device_id = body.get("device_id")
        device_secret = body.get("device_secret")

        if not device_id or not device_secret:
            raise HTTPException(400, "Missing device_id or device_secret")

        # DB에서 디바이스 조회
        result = await db.execute(
            select(Device).where(Device.device_id == device_id)
        )
        device = result.scalar_one_or_none()

        if not device:
            raise HTTPException(401, "Device not found")

        if not device.is_active:
            raise HTTPException(401, "Device is not active")

        # 디바이스 시크릿 검증
        if not pwd_context.verify(device_secret, device.device_secret_hash):
            raise HTTPException(401, "Invalid device secret")

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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Device login failed: {str(e)}")


@router.post("/refresh/device")
async def refresh_device(
    request: Request,
    api_key: str = Depends(verify_api_key),
):
    """
    IoT Device 토큰 갱신 엔드포인트

    Request Body:
        - refresh_token: 현재 refresh token
    """
    from app.auth import get_strategy

    strategy = get_strategy("device")
    result = await strategy.refresh(request)
    return {"success": True, **result}
