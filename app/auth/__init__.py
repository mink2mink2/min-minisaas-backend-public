"""인증 모듈"""
from app.auth.base import AuthStrategy, AuthResult
from app.auth.firebase_verifier import firebase_verifier
from app.auth.jwt_manager import jwt_manager
from app.auth.session_manager import session_manager
from app.auth.web_strategy import WebAuthStrategy
from app.auth.mobile_strategy import MobileAuthStrategy
from app.auth.desktop_strategy import DesktopAuthStrategy
from app.auth.device_strategy import DeviceAuthStrategy

__all__ = [
    "AuthStrategy",
    "AuthResult",
    "firebase_verifier",
    "jwt_manager",
    "session_manager",
    "get_strategy",
    "WebAuthStrategy",
    "MobileAuthStrategy",
    "DesktopAuthStrategy",
    "DeviceAuthStrategy",
]

# 전략 인스턴스
_strategies = {
    "web": WebAuthStrategy(),
    "mobile": MobileAuthStrategy(),
    "desktop": DesktopAuthStrategy(),
    "device": DeviceAuthStrategy(),
}


def get_strategy(platform: str) -> AuthStrategy:
    """
    플랫폼별 인증 전략 조회

    Args:
        platform: "web" | "mobile" | "desktop" | "device"

    Returns:
        해당 플랫폼의 AuthStrategy 인스턴스

    Raises:
        ValueError: 지원하지 않는 플랫폼
    """
    strategy = _strategies.get(platform)
    if not strategy:
        raise ValueError(f"Unknown platform: {platform}")
    return strategy
