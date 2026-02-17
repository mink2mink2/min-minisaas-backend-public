"""설정 모듈"""
from pydantic_settings import BaseSettings
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql://postgres:YOUR_PASSWORD_HERE@localhost:5432/minisaas"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None

    # Security
    SECRET_KEY: str = "REPLACE_WITH_SECURE_RANDOM_KEY"
    API_SECRET_KEY: str = "REPLACE_WITH_SECURE_API_KEY"
    BCRYPT_ROUNDS: int = 12

    # Token TTL
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Session (Web) - 환경별 기본값 설정
    SESSION_TTL_MIN: int = 30
    COOKIE_SECURE: Optional[bool] = None  # None이면 환경에 따라 자동 설정
    COOKIE_SAMESITE: str = "lax"

    def __init__(self, **data):
        super().__init__(**data)

        # COOKIE_SECURE가 명시적으로 설정되지 않으면 환경에 따라 자동 설정
        if self.COOKIE_SECURE is None:
            self.COOKIE_SECURE = (self.ENVIRONMENT == "production")
            # production: True (HTTPS 필수)
            # development: False (HTTP 허용)

    # Desktop Auth
    DESKTOP_ACCESS_EXPIRE_MINUTES: int = 60
    DESKTOP_REFRESH_EXPIRE_DAYS: int = 30

    # IoT Device Auth
    DEVICE_ACCESS_EXPIRE_HOURS: int = 24
    DEVICE_REFRESH_EXPIRE_DAYS: int = 90

    # Firebase
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_JWKS_URI: str = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
    FCM_CREDENTIALS_PATH: Optional[str] = None

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Slack Monitoring
    SLACK_WEBHOOK_URL: Optional[str] = None
    SECURITY_ALERT_THRESHOLD: str = "LOW"  # LOW, MEDIUM, HIGH

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False

    @property
    def REDIS_URL_WITH_AUTH(self) -> str:
        """REDIS_PASSWORD가 있고 URL에 인증정보가 없으면 자동 주입."""
        parsed = urlsplit(self.REDIS_URL)

        if not self.REDIS_PASSWORD or "@" in parsed.netloc:
            return self.REDIS_URL

        netloc = f":{self.REDIS_PASSWORD}@{parsed.netloc}"
        return urlunsplit(
            (parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)
        )

    class Config:
        env_file = ".env"

settings = Settings()
