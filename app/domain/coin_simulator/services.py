"""Coin simulator proxy service backed by local trading server + cache."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.core.cache import cache
from app.core.config import settings
from app.domain.coin_simulator.schemas import (
    CoinSimulatorAssetSummary,
    CoinSimulatorDashboard,
    CoinSimulatorPermissions,
    CoinSimulatorPosition,
    CoinSimulatorSettings,
    CoinSimulatorStatus,
    CoinSimulatorTrade,
)


class CoinSimulatorService:
    _CACHE_KEY = "coin_simulator:dashboard:v1"

    def __init__(self) -> None:
        self._base_url = (settings.LOCAL_COIN_API_BASE_URL or "").rstrip("/")
        self._timeout = settings.LOCAL_COIN_API_TIMEOUT_SECONDS
        self._cache_ttl = settings.COIN_SIMULATOR_CACHE_TTL_SECONDS

    async def get_dashboard(self, *, is_superuser: bool) -> CoinSimulatorDashboard:
        cached = await cache.get(self._CACHE_KEY)
        if cached:
            return self._dashboard_from_cached(cached, is_superuser=is_superuser)

        try:
            dashboard = await self.fetch_live_dashboard(is_superuser=is_superuser)
        except (RuntimeError, httpx.HTTPError):
            return self._build_mock_dashboard(is_superuser=is_superuser)

        await self._store_dashboard(dashboard)
        return dashboard

    async def refresh_dashboard(
        self,
        *,
        is_superuser: bool,
    ) -> CoinSimulatorDashboard:
        dashboard = await self.fetch_live_dashboard(is_superuser=is_superuser)
        await self._store_dashboard(dashboard)
        return dashboard

    async def start(self, *, is_superuser: bool) -> CoinSimulatorDashboard:
        await self._post("/api/bot/start")
        return await self.refresh_dashboard(is_superuser=is_superuser)

    async def stop(self, *, is_superuser: bool) -> CoinSimulatorDashboard:
        await self._post("/api/bot/stop")
        return await self.refresh_dashboard(is_superuser=is_superuser)

    async def update_settings(
        self,
        request: CoinSimulatorSettings,
        *,
        is_superuser: bool,
    ) -> CoinSimulatorDashboard:
        strategy_name = request.enabled_strategies[0] if request.enabled_strategies else "bb_strategy"
        existing = await self._get(f"/api/strategies/{strategy_name}/config")
        current_config = existing.get("config", {}) if isinstance(existing, dict) else {}
        updated_config = self._merge_strategy_config(current_config, request)
        await self._put(
            f"/api/strategies/{strategy_name}/config",
            {"config": updated_config},
        )
        return await self.refresh_dashboard(is_superuser=is_superuser)

    async def fetch_live_dashboard(
        self,
        *,
        is_superuser: bool,
    ) -> CoinSimulatorDashboard:
        self._ensure_live_configured()

        status_payload, positions_payload, trades_payload, pnl_payload, assets_payload = await asyncio.gather(
            self._get("/api/bot/status"),
            self._get("/api/positions", params={"status": "open", "limit": 20}),
            self._get("/api/trades", params={"limit": 10}),
            self._get("/api/pnl/summary"),
            self._get("/api/assets"),
        )

        status_payload = status_payload if isinstance(status_payload, dict) else {}
        positions_payload = positions_payload if isinstance(positions_payload, list) else []
        trades_payload = trades_payload if isinstance(trades_payload, list) else []
        pnl_payload = pnl_payload if isinstance(pnl_payload, dict) else {}
        assets_payload = assets_payload if isinstance(assets_payload, dict) else {}

        strategies = [
            str(item) for item in (status_payload.get("strategies") or ["bb_strategy"])
        ]
        strategy_name = strategies[0] if strategies else "bb_strategy"

        try:
            strategy_payload = await self._get(f"/api/strategies/{strategy_name}/config")
            strategy_config = strategy_payload.get("config", {}) if isinstance(strategy_payload, dict) else {}
        except Exception:
            strategy_config = {}

        exchange = self._extract_exchange(status_payload, assets_payload, strategy_config)
        settings_model = self._map_settings(
            strategy_name=strategy_name,
            strategy_config=strategy_config,
            status_payload=status_payload,
            assets_payload=assets_payload,
            exchange=exchange,
        )

        return CoinSimulatorDashboard(
            data_source="live",
            status=self._map_status(status_payload, exchange=exchange, settings_model=settings_model),
            assets=self._map_assets(assets_payload, pnl_payload),
            positions=self._map_positions(positions_payload),
            recent_trades=self._map_trades(trades_payload),
            settings=settings_model,
            permissions=CoinSimulatorPermissions(
                is_superuser=is_superuser,
                can_control=is_superuser,
                can_configure=is_superuser,
            ),
        )

    async def _store_dashboard(self, dashboard: CoinSimulatorDashboard) -> None:
        payload = dashboard.model_dump(mode="json")
        payload.pop("permissions", None)
        await cache.set(self._CACHE_KEY, payload, ttl_seconds=self._cache_ttl)

    def _dashboard_from_cached(
        self,
        cached: dict[str, Any],
        *,
        is_superuser: bool,
    ) -> CoinSimulatorDashboard:
        payload = deepcopy(cached)
        payload["data_source"] = "cache"
        payload["permissions"] = {
            "is_superuser": is_superuser,
            "can_control": is_superuser,
            "can_configure": is_superuser,
        }
        return CoinSimulatorDashboard.model_validate(payload)

    def _build_mock_dashboard(self, *, is_superuser: bool) -> CoinSimulatorDashboard:
        now = datetime.now(UTC)
        notice = (
            "실제 코인 서버가 연결되지 않아 목업 데이터를 표시 중입니다."
            if self._base_url
            else "Coin simulator 서버 설정이 없어 목업 데이터를 표시 중입니다."
        )
        return CoinSimulatorDashboard(
            data_source="mock",
            notice=notice,
            status=CoinSimulatorStatus(
                running=False,
                mode="PAPER",
                uptime_seconds=0,
                signals_generated=189,
                trades_executed=133,
                exchange="binance",
                strategies=["bb_strategy"],
                candidates=[
                    "BTC-USDT",
                    "ETH-USDT",
                    "SOL-USDT",
                    "XRP-USDT",
                    "DOGE-USDT",
                    "BNB-USDT",
                    "ADA-USDT",
                    "AVAX-USDT",
                ],
                api_usage={"binance": "147 RPM"},
                last_updated=now,
            ),
            assets=CoinSimulatorAssetSummary(
                total_assets=1616.64,
                available_capital=1516.63,
                invested_capital=100.0,
                open_positions=2,
                realized_pnl=16.63,
                unrealized_pnl=0.01,
                total_pnl=16.64,
                win_rate=0.84,
                profit_factor=3.30,
                last_updated=now,
            ),
            positions=[
                CoinSimulatorPosition(
                    symbol="USD1-USDT",
                    side="BUY",
                    strategy="bb_strategy",
                    entry_price=1.0,
                    quantity=50.030018,
                    value=50.0,
                    unrealized_pnl=0.01,
                    stop_loss=0.98,
                    take_profit=1.03,
                    entry_time=now - timedelta(hours=18),
                ),
                CoinSimulatorPosition(
                    symbol="U-USDT",
                    side="BUY",
                    strategy="bb_strategy",
                    entry_price=1.0,
                    quantity=50.005001,
                    value=50.0,
                    unrealized_pnl=-0.01,
                    stop_loss=0.98,
                    take_profit=1.03,
                    entry_time=now - timedelta(hours=9, minutes=15),
                ),
            ],
            recent_trades=[
                CoinSimulatorTrade(
                    symbol="TRX-USDT",
                    strategy="bb_strategy",
                    entry_price=0.12,
                    exit_price=0.1218,
                    quantity=800.0,
                    net_pnl=1.44,
                    return_pct=1.50,
                    duration_seconds=5400,
                    exit_time=now - timedelta(minutes=42),
                ),
                CoinSimulatorTrade(
                    symbol="PEPE-USDT",
                    strategy="bb_strategy",
                    entry_price=0.000012,
                    exit_price=0.0000118,
                    quantity=2000000.0,
                    net_pnl=-0.40,
                    return_pct=-1.67,
                    duration_seconds=3900,
                    exit_time=now - timedelta(hours=2, minutes=10),
                ),
            ],
            settings=CoinSimulatorSettings(
                mode="paper",
                exchange="binance",
                refresh_interval_seconds=5,
                analysis_limit=30,
                default_order_amount=100.0,
                risk_per_trade_pct=1.0,
                auto_stop_loss_pct=2.0,
                auto_take_profit_pct=3.0,
                enabled_strategies=["bb_strategy"],
            ),
            permissions=CoinSimulatorPermissions(
                is_superuser=is_superuser,
                can_control=is_superuser,
                can_configure=is_superuser,
            ),
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        self._ensure_live_configured()
        headers: dict[str, str] = {}
        if settings.LOCAL_COIN_API_KEY:
            headers["X-API-Key"] = settings.LOCAL_COIN_API_KEY
        if settings.LOCAL_COIN_API_BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {settings.LOCAL_COIN_API_BEARER_TOKEN}"

        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
        ) as client:
            response = await client.request(
                method,
                path,
                params=params,
                json=json_body,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    async def _get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def _post(self, path: str, json_body: dict[str, Any] | None = None) -> Any:
        return await self._request("POST", path, json_body=json_body)

    async def _put(self, path: str, json_body: dict[str, Any] | None = None) -> Any:
        return await self._request("PUT", path, json_body=json_body)

    def _ensure_live_configured(self) -> None:
        if not self._base_url:
            raise RuntimeError("LOCAL_COIN_API_BASE_URL is not configured")

    def _extract_exchange(
        self,
        status_payload: dict[str, Any],
        assets_payload: dict[str, Any],
        strategy_config: dict[str, Any],
    ) -> str:
        exchanges = status_payload.get("exchanges")
        if isinstance(exchanges, list) and exchanges:
            return str(exchanges[0])

        balances = assets_payload.get("exchange_balances")
        if isinstance(balances, dict) and balances:
            return str(next(iter(balances.keys())))

        return str(strategy_config.get("exchange") or "binance")

    def _map_status(
        self,
        payload: dict[str, Any],
        *,
        exchange: str,
        settings_model: CoinSimulatorSettings,
    ) -> CoinSimulatorStatus:
        return CoinSimulatorStatus(
            running=payload.get("running") is True,
            mode=str(payload.get("mode") or settings_model.mode).upper(),
            uptime_seconds=int(payload.get("uptime_seconds") or 0),
            signals_generated=int(payload.get("signals_generated") or 0),
            trades_executed=int(payload.get("trades_executed") or 0),
            exchange=exchange,
            strategies=[str(item) for item in payload.get("strategies", [])],
            candidates=[str(item) for item in payload.get("candidates", [])],
            api_usage={
                str(key): str(value)
                for key, value in (payload.get("api_usage") or {}).items()
            },
            last_updated=self._parse_datetime(payload.get("timestamp")),
        )

    def _map_assets(
        self,
        assets_payload: dict[str, Any],
        pnl_payload: dict[str, Any],
    ) -> CoinSimulatorAssetSummary:
        return CoinSimulatorAssetSummary(
            total_assets=self._to_float(assets_payload.get("total_assets")),
            available_capital=self._to_float(assets_payload.get("available_capital")),
            invested_capital=self._to_float(assets_payload.get("open_positions_value")),
            open_positions=int(assets_payload.get("position_count") or 0),
            realized_pnl=self._to_float(pnl_payload.get("realized_pnl")),
            unrealized_pnl=self._to_float(pnl_payload.get("unrealized_pnl")),
            total_pnl=self._to_float(pnl_payload.get("total_pnl")),
            win_rate=self._to_float(pnl_payload.get("win_rate")),
            profit_factor=self._to_float(pnl_payload.get("profit_factor")),
            last_updated=self._parse_datetime(
                assets_payload.get("timestamp") or pnl_payload.get("timestamp"),
            ),
        )

    def _map_positions(self, payload: list[dict[str, Any]]) -> list[CoinSimulatorPosition]:
        return [
            CoinSimulatorPosition(
                symbol=str(item.get("symbol") or ""),
                side=str(item.get("side") or "").upper(),
                strategy=str(item.get("strategy") or ""),
                entry_price=self._to_float(item.get("entry_price")),
                quantity=self._to_float(item.get("quantity")),
                value=self._to_float(item.get("quantity")) * self._to_float(item.get("entry_price")),
                unrealized_pnl=self._to_float(item.get("unrealized_pnl")),
                stop_loss=self._to_float(item.get("stop_loss_price")),
                take_profit=self._to_float(item.get("take_profit_price")),
                entry_time=self._parse_datetime(item.get("entry_time")),
            )
            for item in payload
        ]

    def _map_trades(self, payload: list[dict[str, Any]]) -> list[CoinSimulatorTrade]:
        return [
            CoinSimulatorTrade(
                symbol=str(item.get("symbol") or ""),
                strategy=str(item.get("strategy") or ""),
                entry_price=self._to_float(item.get("entry_price")),
                exit_price=self._to_float(item.get("exit_price")),
                quantity=self._to_float(item.get("quantity")),
                net_pnl=self._to_float(item.get("net_pnl")),
                return_pct=self._to_float(item.get("return_pct")),
                duration_seconds=int(item.get("duration_seconds") or 0),
                exit_time=self._parse_datetime(item.get("exit_time")),
            )
            for item in payload
        ]

    def _map_settings(
        self,
        *,
        strategy_name: str,
        strategy_config: dict[str, Any],
        status_payload: dict[str, Any],
        assets_payload: dict[str, Any],
        exchange: str,
    ) -> CoinSimulatorSettings:
        config = strategy_config if isinstance(strategy_config, dict) else {}
        stop_loss = config.get("stop_loss") if isinstance(config.get("stop_loss"), dict) else {}
        take_profit = config.get("take_profit") if isinstance(config.get("take_profit"), dict) else {}
        return CoinSimulatorSettings(
            mode=str(status_payload.get("mode") or config.get("mode") or "paper").lower(),
            exchange=exchange,
            refresh_interval_seconds=int(
                config.get("refresh_interval_seconds")
                or config.get("scan_interval_seconds")
                or 5
            ),
            analysis_limit=int(config.get("analysis_limit") or config.get("max_symbols") or 30),
            default_order_amount=self._to_float(
                config.get("default_order_amount")
                or config.get("position_size")
                or assets_payload.get("initial_capital")
                or 100.0,
            ),
            risk_per_trade_pct=self._to_float(
                config.get("risk_per_trade_pct")
                or self._nested_get(config, "risk", "risk_per_trade_pct")
                or 1.0,
            ),
            auto_stop_loss_pct=self._to_float(
                config.get("auto_stop_loss_pct")
                or stop_loss.get("stop_loss_pct")
                or 2.0,
            ),
            auto_take_profit_pct=self._to_float(
                config.get("auto_take_profit_pct")
                or take_profit.get("take_profit_pct")
                or 3.0,
            ),
            enabled_strategies=[strategy_name],
        )

    def _merge_strategy_config(
        self,
        current_config: dict[str, Any],
        request: CoinSimulatorSettings,
    ) -> dict[str, Any]:
        updated = deepcopy(current_config) if isinstance(current_config, dict) else {}
        updated["mode"] = request.mode
        updated["exchange"] = request.exchange
        updated["refresh_interval_seconds"] = request.refresh_interval_seconds
        updated["analysis_limit"] = request.analysis_limit
        updated["default_order_amount"] = request.default_order_amount
        updated["risk_per_trade_pct"] = request.risk_per_trade_pct
        updated["auto_stop_loss_pct"] = request.auto_stop_loss_pct
        updated["auto_take_profit_pct"] = request.auto_take_profit_pct
        updated["enabled_strategies"] = request.enabled_strategies

        risk = updated.get("risk") if isinstance(updated.get("risk"), dict) else {}
        risk["risk_per_trade_pct"] = request.risk_per_trade_pct
        updated["risk"] = risk

        stop_loss = updated.get("stop_loss") if isinstance(updated.get("stop_loss"), dict) else {}
        stop_loss["stop_loss_pct"] = request.auto_stop_loss_pct
        updated["stop_loss"] = stop_loss

        take_profit = updated.get("take_profit") if isinstance(updated.get("take_profit"), dict) else {}
        take_profit["take_profit_pct"] = request.auto_take_profit_pct
        updated["take_profit"] = take_profit

        return updated

    def _nested_get(self, payload: dict[str, Any], *keys: str) -> Any:
        current: Any = payload
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    def _to_float(self, value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _parse_datetime(self, value: Any):
        if isinstance(value, str) and value:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass
        return datetime.now(UTC)


coin_simulator_service = CoinSimulatorService()
