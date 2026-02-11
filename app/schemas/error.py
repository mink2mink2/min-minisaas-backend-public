"""Unified error response schemas"""
from pydantic import BaseModel
from typing import Optional


class AuthErrorResponse(BaseModel):
    """Standardized auth error response"""
    success: bool = False
    error_code: str  # "INVALID_CREDENTIALS", "MISSING_FIELD", etc.
    message: str     # Generic message only
    status_code: int


# Unified error messages - no platform-specific details
ERROR_MESSAGES = {
    "INVALID_CREDENTIALS": "Authentication failed",
    "MISSING_FIELD": "Missing required field",
    "INVALID_TOKEN": "Invalid or expired token",
    "DEVICE_LOCKED": "Too many attempts. Try again later.",
    "USER_NOT_FOUND": "Authentication failed",
    "SESSION_EXPIRED": "Session expired. Please login again",
    "TOKEN_REUSE_DETECTED": "Suspicious activity detected. Re-authenticate required.",
    "INVALID_REFRESH_TOKEN": "Invalid or expired refresh token",
    "DEVICE_NOT_FOUND": "Authentication failed",
    "DEVICE_INACTIVE": "Device is not active",
    "AUTHENTICATION_FAILED": "Authentication failed",
    "CODE_EXCHANGE_FAILED": "Authentication failed",
    "SERVER_ERROR": "Server error. Please try again later.",
}
