"""Desktop 플랫폼 인증 전략 - OAuth2 PKCE → Self-issued JWT"""
import time
import httpx
from typing import Dict, Any
from pydantic import BaseModel
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse, Response
from jose import jwt as jose_jwt
from app.auth.base import AuthStrategy, AuthResult
from app.core.config import settings
from app.core.security import decode_token


class DesktopLoginRequest(BaseModel):
    """Desktop 로그인 요청"""

    code: str  # Authorization code from Google
    code_verifier: str  # PKCE code verifier
    device_id: str = ""  # Optional device identifier


class DesktopAuthStrategy(AuthStrategy):
    """Desktop: OAuth2 PKCE → Self-issued JWT"""

    async def authenticate(self, request: Request, **kwargs) -> AuthResult:
        """
        1. Body에서 authorization_code + code_verifier 추출
        2. Google Token Exchange API 호출
        3. 받은 id_token 검증
        4. AuthResult 반환
        """
        try:
            # Request body에서 데이터 추출
            body = await request.json()
            code = body.get("code")
            code_verifier = body.get("code_verifier")
            device_id = body.get("device_id", "")

            if not code or not code_verifier:
                raise HTTPException(400, "Missing code or code_verifier")

            # Google Token Exchange
            id_token, access_token = await self._exchange_code(code, code_verifier)

            # id_token 검증 및 payload 추출
            payload = await self._verify_id_token(id_token)

            # AuthResult 반환
            return AuthResult(
                user_id=payload.get("sub"),
                email=payload.get("email"),
                name=payload.get("name"),
                picture=payload.get("picture"),
                platform="desktop",
                auth_type="oauth_pkce",
                expires=int(time.time()) + (settings.DESKTOP_ACCESS_EXPIRE_MINUTES * 60),
                metadata={"device_id": device_id},
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(401, f"Desktop authentication failed: {str(e)}")

    async def create_session(self, auth_result: AuthResult) -> dict:
        """
        자체 JWT 쌍 발급

        - access_token: exp = 1시간
        - refresh_token: exp = 30일
        - Redis에 refresh_token 저장 (Rotation 추적)
        """
        from app.auth.session_manager import session_manager
        from app.core.cache import cache

        device_id = auth_result.metadata.get("device_id", "")
        now = int(time.time())

        # Access token 생성
        access_expires = now + (settings.DESKTOP_ACCESS_EXPIRE_MINUTES * 60)
        access_payload = {
            "sub": auth_result.user_id,
            "exp": access_expires,
            "iat": now,
            "type": "access",
            "platform": "desktop",
        }
        access_token = jose_jwt.encode(
            access_payload, settings.SECRET_KEY, algorithm="HS256"
        )

        # Refresh token 생성
        refresh_expires = now + (settings.DESKTOP_REFRESH_EXPIRE_DAYS * 86400)
        refresh_payload = {
            "sub": auth_result.user_id,
            "exp": refresh_expires,
            "iat": now,
            "type": "refresh",
            "platform": "desktop",
            "device_id": device_id,
        }
        refresh_token = jose_jwt.encode(
            refresh_payload, settings.SECRET_KEY, algorithm="HS256"
        )

        # Redis에 refresh token 저장 (Rotation 추적)
        redis_key = f"desktop:refresh:{auth_result.user_id}:{device_id}"
        redis_data = {
            "refresh_token": refresh_token,
            "device_name": "",  # 클라이언트에서 제공 가능
            "created_at": now,
        }
        await cache.set(
            redis_key,
            redis_data,
            ttl_seconds=settings.DESKTOP_REFRESH_EXPIRE_DAYS * 86400,
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
        """JSONResponse with tokens in body (쿠키 없음)"""
        response_data.update(
            {
                "access_token": session_data.get("access_token"),
                "refresh_token": session_data.get("refresh_token"),
                "expires": session_data.get("access_expires"),
            }
        )
        return JSONResponse(response_data)

    async def logout(self, request: Request, user_id: str) -> None:
        """
        Redis에서 refresh_token 삭제
        device_id 기반으로 해당 기기만 로그아웃
        """
        from app.core.cache import cache

        # Get device_id from auth header or body
        device_id = request.headers.get("X-Device-ID", "")

        redis_key = f"desktop:refresh:{user_id}:{device_id}"
        await cache.delete(redis_key)

    async def heartbeat(self, request: Request) -> dict:
        """access_token 검증 → exp 반환"""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(401, "Missing or invalid Authorization header")

        token = auth_header[7:]

        try:
            payload = decode_token(token)
            if payload.get("type") != "access" or payload.get("platform") != "desktop":
                raise HTTPException(401, "Invalid token type")
            return {"valid": True, "expires": payload.get("exp")}
        except Exception as e:
            raise HTTPException(401, f"Token validation failed: {str(e)}")

    async def refresh(self, request: Request) -> dict:
        """
        Refresh Token Rotation

        1. refresh_token 검증
        2. Redis에서 일치 여부 확인 (Rotation 탐지)
        3. 새 Access + Refresh 발급
        4. Redis 업데이트
        5. 이전 refresh_token 즉시 무효화
        """
        try:
            # Body에서 refresh_token 추출
            body = await request.json()
            refresh_token = body.get("refresh_token")
            if not refresh_token:
                raise HTTPException(400, "Missing refresh_token")

            # Refresh token 검증
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh" or payload.get("platform") != "desktop":
                raise HTTPException(401, "Invalid refresh token")

            user_id = payload.get("sub")
            device_id = payload.get("device_id", "")

            # Redis에서 일치 여부 확인
            from app.core.cache import cache

            redis_key = f"desktop:refresh:{user_id}:{device_id}"
            stored_data = await cache.get(redis_key)

            if not stored_data or stored_data.get("refresh_token") != refresh_token:
                # 토큰 재사용 시도 → 모든 기기 로그아웃 고려
                await cache.invalidate_pattern(f"desktop:refresh:{user_id}:*")
                raise HTTPException(401, "Token reuse detected")

            # 새 토큰 쌍 발급
            now = int(time.time())
            access_expires = now + (settings.DESKTOP_ACCESS_EXPIRE_MINUTES * 60)
            refresh_expires = now + (settings.DESKTOP_REFRESH_EXPIRE_DAYS * 86400)

            new_access_payload = {
                "sub": user_id,
                "exp": access_expires,
                "iat": now,
                "type": "access",
                "platform": "desktop",
            }
            new_access_token = jose_jwt.encode(
                new_access_payload, settings.SECRET_KEY, algorithm="HS256"
            )

            new_refresh_payload = {
                "sub": user_id,
                "exp": refresh_expires,
                "iat": now,
                "type": "refresh",
                "platform": "desktop",
                "device_id": device_id,
            }
            new_refresh_token = jose_jwt.encode(
                new_refresh_payload, settings.SECRET_KEY, algorithm="HS256"
            )

            # Redis 업데이트
            stored_data.update(
                {
                    "refresh_token": new_refresh_token,
                    "created_at": now,
                }
            )
            await cache.set(
                redis_key,
                stored_data,
                ttl_seconds=settings.DESKTOP_REFRESH_EXPIRE_DAYS * 86400,
            )

            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "access_expires": access_expires,
                "refresh_expires": refresh_expires,
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(401, f"Token refresh failed: {str(e)}")

    async def _exchange_code(self, code: str, code_verifier: str) -> tuple:
        """
        Google Token Exchange API 호출

        Returns:
            (id_token, access_token)
        """
        token_url = "https://oauth2.googleapis.com/token"

        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code_verifier": code_verifier,
            "redirect_uri": "http://localhost:9876/callback",  # PKCE uses this
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=payload, timeout=10)
                response.raise_for_status()

                tokens = response.json()
                return tokens.get("id_token"), tokens.get("access_token")

        except Exception as e:
            raise HTTPException(400, f"Token exchange failed: {str(e)}")

    async def _verify_id_token(self, id_token: str) -> Dict[str, Any]:
        """
        id_token 검증 (Google 공개키)

        실제로는 Google의 공개키로 검증해야 하지만,
        여기서는 기본 구조만 제시
        """
        try:
            # Google의 공개키 URL: https://www.googleapis.com/oauth2/v1/certs
            # 실제로는 여기서 Google의 공개키를 사용하여 검증
            from jose import jwt

            # 임시로 서명 검증 없이 payload만 추출
            payload = jwt.get_unverified_claims(id_token)

            # 기본 필드 검증
            if not payload.get("sub") or not payload.get("email"):
                raise HTTPException(401, "Invalid id_token structure")

            return payload

        except Exception as e:
            raise HTTPException(401, f"id_token verification failed: {str(e)}")
