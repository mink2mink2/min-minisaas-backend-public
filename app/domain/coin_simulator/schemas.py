"""Coin simulator response and request schemas."""
from datetime import datetime
from typing import Dict, List, Literal

from pydantic import BaseModel, Field


class CoinSimulatorStatus(BaseModel):
    running: bool
    mode: str
    uptime_seconds: int
    signals_generated: int
    trades_executed: int
    exchange: str
    strategies: List[str] = Field(default_factory=list)
    candidates: List[str] = Field(default_factory=list)
    api_usage: Dict[str, str] = Field(default_factory=dict)
    last_updated: datetime


class CoinSimulatorAssetSummary(BaseModel):
    total_assets: float
    available_capital: float
    invested_capital: float
    open_positions: int
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    win_rate: float
    profit_factor: float
    last_updated: datetime


class CoinSimulatorPosition(BaseModel):
    symbol: str
    side: Literal["BUY", "SELL"]
    strategy: str
    entry_price: float
    quantity: float
    value: float
    unrealized_pnl: float
    stop_loss: float
    take_profit: float
    entry_time: datetime


class CoinSimulatorTrade(BaseModel):
    symbol: str
    strategy: str
    entry_price: float
    exit_price: float
    quantity: float
    net_pnl: float
    return_pct: float
    duration_seconds: int
    exit_time: datetime


class CoinSimulatorSettings(BaseModel):
    mode: Literal["paper", "live"] = "paper"
    exchange: str = "binance"
    refresh_interval_seconds: int = Field(default=5, ge=1, le=60)
    analysis_limit: int = Field(default=30, ge=5, le=100)
    default_order_amount: float = Field(default=100.0, gt=0)
    risk_per_trade_pct: float = Field(default=1.0, gt=0, le=20)
    auto_stop_loss_pct: float = Field(default=2.0, gt=0, le=20)
    auto_take_profit_pct: float = Field(default=3.0, gt=0, le=50)
    enabled_strategies: List[str] = Field(default_factory=lambda: ["bb_strategy"])


class CoinSimulatorPermissions(BaseModel):
    is_superuser: bool
    can_control: bool
    can_configure: bool


class CoinSimulatorDashboard(BaseModel):
    data_source: Literal["live", "cache", "mock"] = "live"
    notice: str | None = None
    status: CoinSimulatorStatus
    assets: CoinSimulatorAssetSummary
    positions: List[CoinSimulatorPosition] = Field(default_factory=list)
    recent_trades: List[CoinSimulatorTrade] = Field(default_factory=list)
    settings: CoinSimulatorSettings
    permissions: CoinSimulatorPermissions
