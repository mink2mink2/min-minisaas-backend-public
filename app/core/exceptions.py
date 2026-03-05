"""Unified exception handling for authentication"""
import logging
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request
from app.schemas.error import ERROR_MESSAGES

logger = logging.getLogger(__name__)


class AuthException(HTTPException):
    """
    Unified authentication exception

    All auth failures use the same error code + generic message format
    regardless of platform or specific error reason
    """

    def __init__(self, error_code: str, status_code: int = 401):
        self.error_code = error_code
        self.status_code = status_code
        self.message = ERROR_MESSAGES.get(error_code, "Authentication failed")

        # Parent HTTPException init
        super().__init__(status_code=status_code, detail=self.message)


async def auth_exception_handler(request: Request, exc: AuthException) -> JSONResponse:
    """
    Handle AuthException and return unified error response
    """
    logger.warning(
        "AuthException: code=%s status=%s method=%s path=%s platform=%s has_auth=%s ua=%s client=%s",
        exc.error_code,
        exc.status_code,
        request.method,
        request.url.path,
        request.headers.get("X-Platform"),
        bool(request.headers.get("Authorization")),
        request.headers.get("User-Agent"),
        request.client.host if request.client else None,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
        }
    )
