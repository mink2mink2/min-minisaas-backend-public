"""Coin simulator endpoints."""
import logging
import time

import httpx

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import verify_api_key
from app.api.v1.dependencies.auth import verify_any_platform
from app.core.auth import AuthResult
from app.core.cache import cache
from app.core.database import get_db
from app.domain.auth.services.auth_service import AuthService
from app.domain.coin_simulator.schemas import (
    CoinSimulatorDashboard,
    CoinSimulatorSettings,
)
from app.domain.coin_simulator.services import coin_simulator_service

router = APIRouter(prefix="/coin-simulator", tags=["coin-simulator"])
logger = logging.getLogger(__name__)

_CONTROL_RATE_LIMIT_COUNT = 5
_CONTROL_RATE_LIMIT_WINDOW_SECONDS = 60


async def _resolve_is_superuser(
    current_user: AuthResult,
    db: AsyncSession,
) -> bool:
    if current_user.email and AuthService.is_superuser_email(current_user.email):
        return True

    user = await AuthService(db).get_user_by_id(current_user.user_id)
    if not user:
        return False
    return AuthService.is_superuser_email(user.email)


async def _require_superuser(
    current_user: AuthResult,
    db: AsyncSession,
) -> None:
    if not await _resolve_is_superuser(current_user, db):
        raise HTTPException(status_code=403, detail="Superuser privileges required")


async def _enforce_control_rate_limit(current_user: AuthResult) -> None:
    window = int(time.time() // _CONTROL_RATE_LIMIT_WINDOW_SECONDS)
    cache_key = f"coin_simulator:control_rate:{current_user.user_id}:{window}"
    current_count = await cache.get(cache_key) or 0
    current_count = int(current_count)

    if current_count >= _CONTROL_RATE_LIMIT_COUNT:
        raise HTTPException(
            status_code=429,
            detail="Coin simulator 제어 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
        )

    await cache.set(
        cache_key,
        current_count + 1,
        ttl_seconds=_CONTROL_RATE_LIMIT_WINDOW_SECONDS,
    )


def _audit_control_action(
    *,
    action: str,
    current_user: AuthResult,
    request: Request,
    outcome: str,
    detail: str | None = None,
) -> None:
    client_ip = request.client.host if request.client else "unknown"
    logger.info(
        "coin_simulator_control action=%s outcome=%s user_id=%s platform=%s ip=%s detail=%s",
        action,
        outcome,
        current_user.user_id,
        current_user.platform,
        client_ip,
        detail or "-",
    )


@router.get("/dashboard", response_model=CoinSimulatorDashboard)
async def get_dashboard(
    current_user: AuthResult = Depends(verify_any_platform),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    is_superuser = await _resolve_is_superuser(current_user, db)
    try:
        return await coin_simulator_service.get_dashboard(is_superuser=is_superuser)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Coin simulator 서버 설정이 필요합니다: {exc}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail="Coin simulator 로컬 서버에 연결할 수 없습니다. 서버 상태와 인증 설정을 확인해주세요.",
        ) from exc


@router.post("/start", response_model=CoinSimulatorDashboard)
async def start_simulator(
    request: Request,
    current_user: AuthResult = Depends(verify_any_platform),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    await _require_superuser(current_user, db)
    await _enforce_control_rate_limit(current_user)
    try:
        dashboard = await coin_simulator_service.start(is_superuser=True)
        _audit_control_action(
            action="start",
            current_user=current_user,
            request=request,
            outcome="success",
        )
        return dashboard
    except RuntimeError as exc:
        _audit_control_action(
            action="start",
            current_user=current_user,
            request=request,
            outcome="failure",
            detail=str(exc),
        )
        raise HTTPException(
            status_code=503,
            detail=f"Coin simulator 서버 설정이 필요합니다: {exc}",
        ) from exc
    except httpx.HTTPError as exc:
        _audit_control_action(
            action="start",
            current_user=current_user,
            request=request,
            outcome="failure",
            detail=exc.__class__.__name__,
        )
        raise HTTPException(
            status_code=503,
            detail="Coin simulator start 요청을 로컬 서버로 전달하지 못했습니다.",
        ) from exc


@router.post("/stop", response_model=CoinSimulatorDashboard)
async def stop_simulator(
    request: Request,
    current_user: AuthResult = Depends(verify_any_platform),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    await _require_superuser(current_user, db)
    await _enforce_control_rate_limit(current_user)
    try:
        dashboard = await coin_simulator_service.stop(is_superuser=True)
        _audit_control_action(
            action="stop",
            current_user=current_user,
            request=request,
            outcome="success",
        )
        return dashboard
    except RuntimeError as exc:
        _audit_control_action(
            action="stop",
            current_user=current_user,
            request=request,
            outcome="failure",
            detail=str(exc),
        )
        raise HTTPException(
            status_code=503,
            detail=f"Coin simulator 서버 설정이 필요합니다: {exc}",
        ) from exc
    except httpx.HTTPError as exc:
        _audit_control_action(
            action="stop",
            current_user=current_user,
            request=request,
            outcome="failure",
            detail=exc.__class__.__name__,
        )
        raise HTTPException(
            status_code=503,
            detail="Coin simulator stop 요청을 로컬 서버로 전달하지 못했습니다.",
        ) from exc


@router.put("/settings", response_model=CoinSimulatorDashboard)
async def update_settings(
    request: CoinSimulatorSettings,
    http_request: Request,
    current_user: AuthResult = Depends(verify_any_platform),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    await _require_superuser(current_user, db)
    await _enforce_control_rate_limit(current_user)
    try:
        dashboard = await coin_simulator_service.update_settings(
            request,
            is_superuser=True,
        )
        _audit_control_action(
            action="settings",
            current_user=current_user,
            request=http_request,
            outcome="success",
        )
        return dashboard
    except RuntimeError as exc:
        _audit_control_action(
            action="settings",
            current_user=current_user,
            request=http_request,
            outcome="failure",
            detail=str(exc),
        )
        raise HTTPException(
            status_code=503,
            detail=f"Coin simulator 서버 설정이 필요합니다: {exc}",
        ) from exc
    except httpx.HTTPError as exc:
        _audit_control_action(
            action="settings",
            current_user=current_user,
            request=http_request,
            outcome="failure",
            detail=exc.__class__.__name__,
        )
        raise HTTPException(
            status_code=503,
            detail="Coin simulator 설정 저장 요청을 로컬 서버로 전달하지 못했습니다.",
        ) from exc
