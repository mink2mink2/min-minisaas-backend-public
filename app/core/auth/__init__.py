from app.core.auth.base import AuthStrategy, AuthResult
from app.core.auth.jwt_manager import jwt_manager
from app.core.auth.session_manager import session_manager
from app.core.auth.csrf_manager import CSRFTokenManager
from app.core.auth.strategies.web_strategy import WebAuthStrategy
from app.core.auth.strategies.mobile_strategy import MobileAuthStrategy
from app.core.auth.strategies.desktop_strategy import DesktopAuthStrategy
from app.core.auth.strategies.device_strategy import DeviceAuthStrategy


_strategies: dict[str, AuthStrategy] = {
    "web": WebAuthStrategy(),
    "mobile": MobileAuthStrategy(),
    "desktop": DesktopAuthStrategy(),
    "device": DeviceAuthStrategy(),
}


def get_strategy(platform: str) -> AuthStrategy:
    strategy = _strategies.get(platform)
    if not strategy:
        raise ValueError(f"Unknown platform: {platform}")
    return strategy
