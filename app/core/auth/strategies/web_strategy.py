"""Web 플랫폼 인증 전략 - Firebase JWT → Server Session + HttpOnly Cookie"""
import time
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from app.core.auth.base import AuthStrategy, AuthResult
from app.core.auth.firebase_verifier import firebase_verifier
from app.core.auth.jwt_manager import jwt_manager
from app.core.auth.session_manager import session_manager
from app.core.config import settings
from app.core.exceptions import AuthException


class WebAuthStrategy(AuthStrategy):
    """Web: Firebase JWT → Server Session + HttpOnly Cookie"""

    async def authenticate(self, request: Request, **kwargs) -> AuthResult:
        """
        1. Authorization 헤더에서 Firebase JWT 추출
        2. firebase_verifier.verify() 호출
        3. JWT 재사용 체크
        4. AuthResult 반환
        """
        # Authorization 헤더에서 토큰 추출
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise AuthException("INVALID_TOKEN", 401)

        token = auth_header[7:]  # "Bearer " 제거

        # Firebase JWT 검증
        try:
            payload = await firebase_verifier.verify(token)
        except Exception:
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
            raise AuthException("INVALID_TOKEN", 401)

        # AuthResult 반환
        return AuthResult(
            user_id=payload.get("sub"),
            email=payload.get("email"),
            name=payload.get("name"),
            picture=payload.get("picture"),
            platform="web",
            auth_type="firebase",
            expires=exp,
            metadata={"iat": iat},
        )

    async def create_session(self, auth_result: AuthResult) -> dict:
        """
        1. 로그인 전 쿠키에서 old session ID 추출 (Session Fixation 방지)
        2. Old session ID 파괴 (공격자가 미리 설정했을 수 있으므로)
        3. 기존 사용자 세션 파괴 (동시 세션 1개 제한)
        4. 새 세션 생성
        5. 세션 정보 반환
        """
        # 🔴 Step 1: Session Fixation 공격 방지
        # 공격 시나리오: 공격자가 session=ATTACKER_ID를 미리 쿠키에 설정
        # → 사용자 로그인 시 같은 쿠키 ID를 사용하면 공격자도 접근 가능
        # 해결: 로그인 전 쿠키의 session ID를 명시적으로 파괴
        request = auth_result.metadata.get("request")
        if request:
            old_session_id = request.cookies.get("session")
            if old_session_id:
                # Old session이 있으면 파괴 (있든 없든 상관없음)
                await session_manager.destroy(old_session_id)

        # Step 2: 기존 사용자 세션 파괴 (동시 세션 1개 제한)
        await session_manager.destroy_user_sessions(auth_result.user_id)

        # Step 3: 새 세션 생성 (항상 새로운 ID)
        session_id = await session_manager.create(auth_result.user_id)

        # Step 4: 세션 정보 반환
        return {
            "session_id": session_id,
            "expires": auth_result.expires,
        }

    async def build_response(
        self, response_data: dict, session_data: dict
    ) -> Response:
        """
        JSONResponse + Set-Cookie (HttpOnly, Secure, SameSite=Lax)
        """
        response = JSONResponse(response_data)

        # Set-Cookie 헤더 설정
        session_id = session_data.get("session_id")
        expires = session_data.get("expires")

        # Cookie 만료 시간 계산 (세션 TTL의 2배)
        max_age = (expires - int(time.time())) * 2

        response.set_cookie(
            key="session",
            value=session_id,
            max_age=max(max_age, 1),
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            path="/",
        )

        return response

    async def logout(self, request: Request, user_id: str) -> None:
        """
        1. 쿠키에서 session_id 추출
        2. session_manager.destroy(session_id)
        3. jwt_manager.revoke_all_user_jwts(user_id)
        """
        session_id = request.cookies.get("session")
        if session_id:
            await session_manager.destroy(session_id)

        # JWT 무효화
        await jwt_manager.revoke_user_jwts(user_id)

    async def heartbeat(self, request: Request) -> dict:
        """
        1. 쿠키에서 session_id 추출
        2. session_manager.validate_and_slide(session_id)
        3. 갱신된 만료 시각 반환
        """
        session_id = request.cookies.get("session")
        if not session_id:
            raise AuthException("SESSION_EXPIRED", 401)

        session_data = await session_manager.validate_and_slide(session_id)
        if not session_data:
            raise AuthException("SESSION_EXPIRED", 401)

        return {
            "valid": True,
            "expires": session_data.get("expires"),
        }

    async def refresh(self, request: Request) -> dict:
        """
        Web은 세션 기반이므로 heartbeat가 refresh 역할
        heartbeat()로 위임
        """
        return await self.heartbeat(request)
