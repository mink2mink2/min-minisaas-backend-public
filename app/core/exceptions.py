"""Unified exception handling for authentication"""
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request
from app.schemas.error import ERROR_MESSAGES


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
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
        }
    )
