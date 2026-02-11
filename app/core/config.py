"""설정 모듈"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql://postgres:YOUR_PASSWORD_HERE@localhost:5432/minisaas"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "REPLACE_WITH_SECURE_RANDOM_KEY"
    API_SECRET_KEY: str = "REPLACE_WITH_SECURE_API_KEY"
    BCRYPT_ROUNDS: int = 12

    # Token TTL
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Session (Web)
    SESSION_TTL_MIN: int = 30
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "lax"

    # Desktop Auth
    DESKTOP_ACCESS_EXPIRE_MINUTES: int = 60
    DESKTOP_REFRESH_EXPIRE_DAYS: int = 30

    # IoT Device Auth
    DEVICE_ACCESS_EXPIRE_HOURS: int = 24
    DEVICE_REFRESH_EXPIRE_DAYS: int = 90

    # Firebase
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_JWKS_URI: str = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Slack Monitoring
    SLACK_WEBHOOK_URL: Optional[str] = None
    SECURITY_ALERT_THRESHOLD: str = "LOW"  # LOW, MEDIUM, HIGH

    class Config:
        env_file = ".env"

settings = Settings()