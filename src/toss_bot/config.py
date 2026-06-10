from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

from .models import RunMode


class TossSettings(BaseModel):
    base_url: str = "https://openapi.tossinvest.com"
    token_refresh_margin_seconds: int = 60
    timeout_seconds: int = 10


class UniverseSettings(BaseModel):
    markets: list[Literal["KOSPI", "KOSDAQ"]] = Field(default_factory=lambda: ["KOSPI", "KOSDAQ"])
    liquidity_top_n: int = 200
    watch_top_n: int = 60
    min_trading_value_krw: int = 3_000_000_000
    include_etf: bool = False
    excluded_warning_types: list[str] = Field(default_factory=list)


class StrategySettings(BaseModel):
    max_positions: int = 8
    momentum_windows: list[int] = Field(default_factory=lambda: [20, 60, 120])
    momentum_weights: list[float] = Field(default_factory=lambda: [0.5, 0.3, 0.2])
    volatility_window: int = 20
    trend_quality_weight: float = 0.20
    volume_accumulation_weight: float = 0.10
    high_proximity_weight: float = 0.10
    liquidity_weight: float = 0.10
    min_score: float = 0.5
    min_20d_return_pct: float = 0.03
    min_60d_return_pct: float = 0.05
    max_5d_return_pct: float = 0.25
    max_drawdown_from_high_pct: float = 0.30
    min_volume_accumulation_ratio: float = 0.85
    max_distance_from_ma20_pct: float = 0.18
    max_gap_up_pct: float = 0.07
    max_intraday_extension_pct: float = 0.08
    breakout_buffer_pct: float = 0.001
    require_trend_alignment: bool = True
    require_vwap_confirmation: bool = True
    volume_spike_multiplier: float = 1.5
    intraday_box_minutes: int = 20
    stop_loss_pct: float = 0.04
    trailing_stop_pct: float = 0.03
    breakeven_trigger_pct: float = 0.025
    breakeven_buffer_pct: float = 0.003
    profit_lock_trigger_pct: float = 0.08
    profit_lock_trailing_stop_pct: float = 0.02
    daily_drop_exit_pct: float = 0.035
    max_holding_days: int = 10
    new_entries_cutoff: str = "15:20"
    forced_exit_window_start: str = "15:25"
    forced_exit_window_end: str = "15:30"

    @field_validator("momentum_weights")
    @classmethod
    def weights_must_match_windows(cls, value: list[float], info):
        windows = info.data.get("momentum_windows", [])
        if windows and len(value) != len(windows):
            raise ValueError("momentum_weights must match momentum_windows length")
        return value


class RiskSettings(BaseModel):
    max_symbol_weight: float = 0.18
    min_cash_weight: float = 0.10
    target_position_volatility_pct: float = 0.025
    max_entry_risk_pct: float = 0.008
    min_order_amount_krw: int = 50_000
    daily_loss_limit_pct: float = 0.03
    weekly_loss_limit_pct: float = 0.08
    max_drawdown_pct: float = 0.15
    max_live_order_amount_krw: int = 1_000_000
    min_paper_trading_days: int = 20
    paper_trading_days_completed: int = 0
    commission_rate: float = 0.00015
    transaction_tax_rate: float = 0.002
    slippage_bps: int = 8


class ScheduleSettings(BaseModel):
    preflight_time: str = "08:30"
    premarket_report_time: str = "08:50"
    market_loop_start: str = "09:00"
    market_loop_end: str = "15:20"
    close_policy_start: str = "15:25"
    close_policy_end: str = "15:30"
    reconcile_interval_minutes: int = 5
    report_time: str = "15:40"


class ExecutionSettings(BaseModel):
    max_entry_spread_bps: int = 25
    max_exit_spread_bps: int = 80
    max_chase_bps: int = 20
    max_orderbook_participation: float = 0.25
    price_limit_buffer_pct: float = 0.01
    stale_order_minutes: int = 3
    cancel_stale_orders: bool = True


class PaperSettings(BaseModel):
    initial_cash_krw: int = 10_000_000


class Settings(BaseModel):
    mode: RunMode = RunMode.PAPER
    timezone: str = "Asia/Seoul"
    database_url: str = "sqlite:///data/toss_bot.sqlite3"
    reports_dir: str = "reports"
    toss: TossSettings = Field(default_factory=TossSettings)
    universe: UniverseSettings = Field(default_factory=UniverseSettings)
    strategy: StrategySettings = Field(default_factory=StrategySettings)
    risk: RiskSettings = Field(default_factory=RiskSettings)
    execution: ExecutionSettings = Field(default_factory=ExecutionSettings)
    schedule: ScheduleSettings = Field(default_factory=ScheduleSettings)
    paper: PaperSettings = Field(default_factory=PaperSettings)

    toss_client_id: str | None = None
    toss_client_secret: str | None = None
    toss_account_seq: int | None = None
    discord_webhook_url: str | None = None
    enable_live_trading: bool = False


def load_settings(path: str | Path = "config/settings.yaml") -> Settings:
    load_dotenv()
    settings_path = Path(path)
    raw = yaml.safe_load(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    data = dict(raw or {})
    data.update(
        {
            "toss_client_id": os.getenv("TOSSINVEST_CLIENT_ID") or None,
            "toss_client_secret": os.getenv("TOSSINVEST_CLIENT_SECRET") or None,
            "discord_webhook_url": os.getenv("DISCORD_WEBHOOK_URL") or None,
            "enable_live_trading": os.getenv("ENABLE_LIVE_TRADING", "false").lower() == "true",
        }
    )
    account_seq = os.getenv("TOSSINVEST_ACCOUNT_SEQ")
    if account_seq:
        data["toss_account_seq"] = int(account_seq)
    return Settings.model_validate(data)
