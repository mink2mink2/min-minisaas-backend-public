"""인증 전략 추상 클래스"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from fastapi import Request
from fastapi.responses import Response


@dataclass
class AuthResult:
    """인증 결과 (모든 전략이 동일한 형태로 반환)"""
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    platform: str = "web"  # "web" | "mobile" | "desktop" | "device"
    auth_type: str = "unknown"  # "firebase" | "oauth_pkce" | "api_key"
    expires: int = 0  # 세션/토큰 만료 Unix timestamp
    metadata: Dict[str, Any] = field(default_factory=dict)


class AuthStrategy(ABC):
    """인증 전략 인터페이스"""

    @abstractmethod
    async def authenticate(self, request: Request, **kwargs) -> AuthResult:
        """인증 수행 - 클라이언트 자격증명 검증 후 AuthResult 반환"""
        ...

    @abstractmethod
    async def create_session(self, auth_result: AuthResult) -> dict:
        """세션/토큰 생성"""
        ...

    @abstractmethod
    async def build_response(self, response_data: dict, session_data: dict) -> Response:
        """최종 HTTP 응답 생성"""
        ...

    @abstractmethod
    async def logout(self, request: Request, user_id: str) -> None:
        """로그아웃 처리"""
        ...

    @abstractmethod
    async def heartbeat(self, request: Request) -> dict:
        """세션/토큰 유효성 확인"""
        ...

    @abstractmethod
    async def refresh(self, request: Request) -> dict:
        """토큰 갱신 (해당하는 전략만)"""
        ...
