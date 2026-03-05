"""Mobile 플랫폼 인증 전략 - Firebase JWT (Stateless)"""
import logging
import time
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from app.core.auth.base import AuthStrategy, AuthResult
from app.core.auth.firebase_verifier import firebase_verifier
from app.core.auth.jwt_manager import jwt_manager
from app.core.exceptions import AuthException

logger = logging.getLogger(__name__)


class MobileAuthStrategy(AuthStrategy):
    """Mobile: Firebase JWT (Stateless)"""

    async def authenticate(self, request: Request, **kwargs) -> AuthResult:
        """
        1. Authorization 헤더에서 Firebase JWT 추출
        2. firebase_verifier.verify() 호출
        3. JWT 재사용 체크
        4. AuthResult 반환 (expires = JWT exp)
        """
        # Authorization 헤더에서 토큰 추출
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise AuthException("INVALID_TOKEN", 401)

        token = auth_header[7:]  # "Bearer " 제거

        # Firebase JWT 검증
        try:
            payload = await firebase_verifier.verify(token)
        except Exception as e:
            logger.warning(
                "Mobile auth verify failed: path=%s has_auth=%s platform=%s client=%s reason=%s",
                request.url.path,
                bool(auth_header),
                request.headers.get("X-Platform"),
                request.client.host if request.client else None,
                str(e),
            )
            raise AuthException("INVALID_TOKEN", 401)

        # JWT 재사용 방지 체크
        iat = payload.get("iat", int(time.time()))
        exp = payload.get("exp", int(time.time()) + 3600)

        is_new = await jwt_manager.check_and_mark_used(
            user_id=payload.get("sub"),
            iat=iat,
            exp=exp,
        )

        if not is_new:
            logger.warning(
                "Mobile auth replay detected: path=%s sub=%s iat=%s exp=%s",
                request.url.path,
                payload.get("sub"),
                iat,
                exp,
            )
            raise AuthException("INVALID_TOKEN", 401)

        # AuthResult 반환
        return AuthResult(
            user_id=payload.get("sub"),
            email=payload.get("email"),
            name=payload.get("name"),
            picture=payload.get("picture"),
            platform="mobile",
            auth_type="firebase",
            expires=exp,
            metadata={"iat": iat},
        )

    async def create_session(self, auth_result: AuthResult) -> dict:
        """
        Stateless - 세션 생성 안 함
        """
        return {"expires": auth_result.expires}

    async def build_response(
        self, response_data: dict, session_data: dict
    ) -> Response:
        """
        JSONResponse only (쿠키 없음)
        """
        return JSONResponse(response_data)

    async def logout(self, request: Request, user_id: str) -> None:
        """
        Stateless - 서버에서 할 것 없음
        클라이언트가 토큰 삭제
        """
        # JWT 무효화 (선택적)
        await jwt_manager.revoke_user_jwts(user_id)

    async def heartbeat(self, request: Request) -> dict:
        """
        Firebase JWT 검증만 수행
        JWT exp 반환
        """
        # Authorization 헤더에서 토큰 추출
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise AuthException("INVALID_TOKEN", 401)

        token = auth_header[7:]

        # Firebase JWT 검증
        try:
            payload = await firebase_verifier.verify(token)
        except Exception as e:
            logger.warning(
                "Mobile heartbeat verify failed: path=%s has_auth=%s platform=%s client=%s reason=%s",
                request.url.path,
                bool(auth_header),
                request.headers.get("X-Platform"),
                request.client.host if request.client else None,
                str(e),
            )
            raise AuthException("INVALID_TOKEN", 401)

        return {
            "valid": True,
            "expires": payload.get("exp"),
        }

    async def refresh(self, request: Request) -> dict:
        """
        Firebase SDK가 자동 갱신하므로 서버에서 처리 불필요
        """
        raise AuthException("AUTHENTICATION_FAILED", 501)
