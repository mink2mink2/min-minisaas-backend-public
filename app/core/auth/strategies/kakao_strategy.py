"""Kakao OAuth 인증 전략"""
from pydantic import BaseModel
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from app.core.auth.base import AuthStrategy, AuthResult
from app.core.auth.kakao_verifier import kakao_verifier
from app.core.exceptions import AuthException


class KakaoLoginRequest(BaseModel):
    """Kakao 로그인 요청"""
    kakao_access_token: str


class KakaoOAuthStrategy(AuthStrategy):
    """Kakao: Kakao OAuth API → Stateless"""

    async def authenticate(self, request: Request, **kwargs) -> AuthResult:
        """
        1. Body에서 kakao_access_token 추출
        2. kakao_verifier.verify() 호출
        3. AuthResult 반환
        """
        try:
            # Body 파싱
            body = await request.json()
            kakao_access_token = body.get("kakao_access_token")
        except Exception:
            raise AuthException("INVALID_REQUEST", 400)

        if not kakao_access_token:
            raise AuthException("MISSING_TOKEN", 400)

        # Kakao 토큰 검증 및 사용자 정보 조회
        try:
            user_info = await kakao_verifier.verify(kakao_access_token)
        except AuthException:
            raise
        except Exception as e:
            raise AuthException("AUTHENTICATION_FAILED", 401)

        # AuthResult 반환
        return AuthResult(
            user_id=user_info["user_id"],
            email=user_info.get("email"),
            name=user_info.get("nickname"),
            picture=user_info.get("picture"),
            platform="mobile",  # OAuth는 mobile처럼 stateless
            auth_type="kakao_oauth",
            expires=0,
            metadata={"raw_data": user_info.get("raw_data", {})},
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
        pass

    async def heartbeat(self, request: Request) -> dict:
        """
        Kakao는 stateless이므로 heartbeat 불필요
        """
        raise AuthException("NOT_IMPLEMENTED", 501)

    async def refresh(self, request: Request) -> dict:
        """
        Kakao는 클라이언트가 갱신하므로 서버에서 처리 불필요
        """
        raise AuthException("NOT_IMPLEMENTED", 501)
