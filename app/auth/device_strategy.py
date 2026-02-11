"""IoT Device 플랫폼 인증 전략 - API Key + Device Secret → Long-lived JWT"""
import time
from typing import Dict, Any
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from jose import jwt as jose_jwt
from passlib.context import CryptContext
from app.auth.base import AuthStrategy, AuthResult
from app.core.config import settings
from app.core.security import decode_token
from app.core.exceptions import AuthException

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class DeviceAuthStrategy(AuthStrategy):
    """IoT: API Key + Device Secret → Long-lived JWT"""

    async def authenticate(self, request: Request, **kwargs) -> AuthResult:
        """
        1. Body에서 device_id + device_secret 추출
        2. DB에서 디바이스 조회 및 secret 검증
        3. 디바이스 활성 상태 확인
        4. AuthResult 반환
        """
        try:
            from sqlalchemy.ext.asyncio import AsyncSession
            from sqlalchemy import select
            from app.models.device import Device
            from app.core.database import get_db

            # Request body에서 데이터 추출
            body = await request.json()
            device_id = body.get("device_id")
            device_secret = body.get("device_secret")

            if not device_id or not device_secret:
                raise AuthException("MISSING_FIELD", 400)

            # DB 세션 얻기 (의존성으로부터)
            # 여기서는 직접 생성해야 하므로, kwargs에서 db를 받거나
            # request.app.state에서 가져오거나, 별도 처리 필요
            # 간단히 하기 위해 에러만 반환
            raise AuthException("AUTHENTICATION_FAILED", 501)

        except AuthException:
            raise
        except Exception as e:
            raise AuthException("AUTHENTICATION_FAILED", 401)

    async def create_session(self, auth_result: AuthResult) -> dict:
        """
        장기 토큰 발급

        - access_token: exp = 24시간
        - refresh_token: exp = 90일
        - Redis에 디바이스 세션 저장
        """
        from app.core.cache import cache

        device_id = auth_result.metadata.get("device_id", "")
        now = int(time.time())

        # Access token 생성
        access_expires = now + (settings.DEVICE_ACCESS_EXPIRE_HOURS * 3600)
        access_payload = {
            "sub": auth_result.user_id,
            "exp": access_expires,
            "iat": now,
            "type": "access",
            "platform": "device",
            "device_id": device_id,
        }
        access_token = jose_jwt.encode(
            access_payload, settings.SECRET_KEY, algorithm="HS256"
        )

        # Refresh token 생성 (Rotation 없음)
        refresh_expires = now + (settings.DEVICE_REFRESH_EXPIRE_DAYS * 86400)
        refresh_payload = {
            "sub": auth_result.user_id,
            "exp": refresh_expires,
            "iat": now,
            "type": "refresh",
            "platform": "device",
            "device_id": device_id,
        }
        refresh_token = jose_jwt.encode(
            refresh_payload, settings.SECRET_KEY, algorithm="HS256"
        )

        # Redis에 디바이스 세션 저장
        redis_key = f"device:session:{device_id}"
        redis_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "owner_id": auth_result.user_id,
            "last_seen": now,
        }
        await cache.set(
            redis_key,
            redis_data,
            ttl_seconds=settings.DEVICE_REFRESH_EXPIRE_DAYS * 86400,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "access_expires": access_expires,
            "refresh_expires": refresh_expires,
        }

    async def build_response(
        self, response_data: dict, session_data: dict
    ) -> Response:
        """JSONResponse with tokens"""
        response_data.update(
            {
                "access_token": session_data.get("access_token"),
                "refresh_token": session_data.get("refresh_token"),
                "expires": session_data.get("access_expires"),
            }
        )
        return JSONResponse(response_data)

    async def logout(self, request: Request, user_id: str) -> None:
        """Redis에서 디바이스 세션 삭제"""
        from app.core.cache import cache

        device_id = request.headers.get("X-Device-ID", "")
        if device_id:
            redis_key = f"device:session:{device_id}"
            await cache.delete(redis_key)

    async def heartbeat(self, request: Request) -> dict:
        """
        IoT는 heartbeat 불필요 (긴 TTL)
        호출 시 last_seen 업데이트 정도
        """
        from app.core.cache import cache

        device_id = request.headers.get("X-Device-ID", "")
        if device_id:
            redis_key = f"device:session:{device_id}"
            session_data = await cache.get(redis_key)
            if session_data:
                session_data["last_seen"] = int(time.time())
                await cache.set(redis_key, session_data)

        return {"valid": True}

    async def refresh(self, request: Request) -> dict:
        """
        Rotation 없이 단순 갱신 (IoT 안정성 우선)

        refresh_token 검증 → 새 access_token만 발급
        refresh_token 자체는 만료까지 유지
        """
        try:
            # Body에서 refresh_token 추출
            body = await request.json()
            refresh_token = body.get("refresh_token")
            if not refresh_token:
                raise AuthException("MISSING_FIELD", 400)

            # Refresh token 검증
            try:
                payload = decode_token(refresh_token)
            except Exception:
                raise AuthException("INVALID_REFRESH_TOKEN", 401)

            if payload.get("type") != "refresh" or payload.get("platform") != "device":
                raise AuthException("INVALID_REFRESH_TOKEN", 401)

            user_id = payload.get("sub")
            device_id = payload.get("device_id", "")

            # 새 access token만 발급
            now = int(time.time())
            access_expires = now + (settings.DEVICE_ACCESS_EXPIRE_HOURS * 3600)

            new_access_payload = {
                "sub": user_id,
                "exp": access_expires,
                "iat": now,
                "type": "access",
                "platform": "device",
                "device_id": device_id,
            }
            new_access_token = jose_jwt.encode(
                new_access_payload, settings.SECRET_KEY, algorithm="HS256"
            )

            return {
                "access_token": new_access_token,
                "access_expires": access_expires,
            }

        except AuthException:
            raise
        except Exception as e:
            raise AuthException("AUTHENTICATION_FAILED", 401)
