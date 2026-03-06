from types import SimpleNamespace

import pytest

from app.domain.coin_simulator.schemas import (
    CoinSimulatorAssetSummary,
    CoinSimulatorDashboard,
    CoinSimulatorPermissions,
    CoinSimulatorSettings,
    CoinSimulatorStatus,
)
from app.domain.auth.services.auth_service import AuthService
from app.domain.coin_simulator.services import coin_simulator_service


def _dashboard(is_superuser: bool) -> CoinSimulatorDashboard:
    return CoinSimulatorDashboard(
        data_source="live",
        notice=None,
        status=CoinSimulatorStatus(
            running=True,
            mode="PAPER",
            uptime_seconds=120,
            signals_generated=10,
            trades_executed=3,
            exchange="binance",
            strategies=["bb_strategy"],
            candidates=["BTC-USDT"],
            api_usage={"binance": "12 RPM"},
            last_updated="2026-03-06T12:00:00Z",
        ),
        assets=CoinSimulatorAssetSummary(
            total_assets=1000,
            available_capital=900,
            invested_capital=100,
            open_positions=1,
            realized_pnl=12,
            unrealized_pnl=-1,
            total_pnl=11,
            win_rate=60,
            profit_factor=1.5,
            last_updated="2026-03-06T12:00:00Z",
        ),
        positions=[],
        recent_trades=[],
        settings=CoinSimulatorSettings(
            mode="paper",
            exchange="binance",
            refresh_interval_seconds=5,
            analysis_limit=30,
            default_order_amount=100,
            risk_per_trade_pct=1,
            auto_stop_loss_pct=2,
            auto_take_profit_pct=3,
            enabled_strategies=["bb_strategy"],
        ),
        permissions=CoinSimulatorPermissions(
            is_superuser=is_superuser,
            can_control=is_superuser,
            can_configure=is_superuser,
        ),
    )


def test_coin_simulator_dashboard_is_public_for_authenticated_user(
    client,
    monkeypatch,
):
    async def mock_get_user_by_id(self, user_id):
        return SimpleNamespace(email="viewer@test.com")

    monkeypatch.setattr(AuthService, "get_user_by_id", mock_get_user_by_id)

    async def mock_get_dashboard(*, is_superuser: bool):
        return _dashboard(is_superuser)

    monkeypatch.setattr(coin_simulator_service, "get_dashboard", mock_get_dashboard)

    response = client.get(
        "/api/v1/coin-simulator/dashboard",
        headers={"X-API-Key": "test_key", "X-Platform": "web"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["permissions"]["can_control"] is False
    assert "status" in body
    assert "positions" in body


def test_coin_simulator_start_requires_superuser(
    client,
    monkeypatch,
):
    async def mock_get_user_by_id(self, user_id):
        return SimpleNamespace(email="viewer@test.com")

    monkeypatch.setattr(AuthService, "get_user_by_id", mock_get_user_by_id)

    async def mock_start(*, is_superuser: bool):
        return _dashboard(is_superuser)

    monkeypatch.setattr(coin_simulator_service, "start", mock_start)

    response = client.post(
        "/api/v1/coin-simulator/start",
        headers={"X-API-Key": "test_key", "X-Platform": "web"},
    )

    assert response.status_code == 403


def test_coin_simulator_superuser_can_update_settings(
    client,
    monkeypatch,
):
    async def mock_get_user_by_id(self, user_id):
        return SimpleNamespace(email="admin@test.com")

    monkeypatch.setattr(AuthService, "get_user_by_id", mock_get_user_by_id)
    monkeypatch.setattr(
        "app.core.config.settings.SUPERUSER_EMAILS",
        ["admin@test.com"],
    )

    async def mock_update_settings(request, *, is_superuser: bool):
        return _dashboard(is_superuser)

    monkeypatch.setattr(
        coin_simulator_service,
        "update_settings",
        mock_update_settings,
    )

    response = client.put(
        "/api/v1/coin-simulator/settings",
        headers={"X-API-Key": "test_key", "X-Platform": "web"},
        json={
            "mode": "paper",
            "exchange": "binance",
            "refresh_interval_seconds": 10,
            "analysis_limit": 25,
            "default_order_amount": 250,
            "risk_per_trade_pct": 1.2,
            "auto_stop_loss_pct": 2.5,
            "auto_take_profit_pct": 4.0,
            "enabled_strategies": ["bb_strategy"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["permissions"]["can_configure"] is True
    assert body["settings"]["default_order_amount"] == 100


def test_coin_simulator_control_rate_limit_applies_to_superuser(
    client,
    monkeypatch,
):
    async def mock_get_user_by_id(self, user_id):
        return SimpleNamespace(email="admin@test.com")

    monkeypatch.setattr(AuthService, "get_user_by_id", mock_get_user_by_id)
    monkeypatch.setattr(
        "app.core.config.settings.SUPERUSER_EMAILS",
        ["admin@test.com"],
    )

    async def mock_start(*, is_superuser: bool):
        return _dashboard(is_superuser)

    monkeypatch.setattr(coin_simulator_service, "start", mock_start)

    headers = {"X-API-Key": "test_key", "X-Platform": "web"}

    for _ in range(5):
        response = client.post("/api/v1/coin-simulator/start", headers=headers)
        assert response.status_code == 200

    limited_response = client.post("/api/v1/coin-simulator/start", headers=headers)

    assert limited_response.status_code == 429
    assert "너무 많습니다" in limited_response.json()["detail"]


@pytest.mark.asyncio
async def test_coin_simulator_dashboard_returns_mock_when_live_unavailable(
    monkeypatch,
):
    async def mock_cache_get(_key):
        return None

    async def mock_fetch_live_dashboard(*, is_superuser: bool):
        raise RuntimeError("LOCAL_COIN_API_BASE_URL is not configured")

    monkeypatch.setattr("app.domain.coin_simulator.services.cache.get", mock_cache_get)
    monkeypatch.setattr(
        coin_simulator_service,
        "fetch_live_dashboard",
        mock_fetch_live_dashboard,
    )

    dashboard = await coin_simulator_service.get_dashboard(is_superuser=False)

    assert dashboard.data_source == "mock"
    assert dashboard.notice is not None
    assert dashboard.permissions.can_control is False
