from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

from .markets import DEFAULT_US_SYMBOLS
from .models import MarketCountry, RunMode


class TossSettings(BaseModel):
    base_url: str = "https://openapi.tossinvest.com"
    token_refresh_margin_seconds: int = 60
    timeout_seconds: int = 10


class CostSettings(BaseModel):
    """시장별 매매 비용. sell_fee_rate는 KR이면 거래세+농특세, US면 SEC fee+TAF 근사치."""

    commission_rate: float = 0.00015
    sell_fee_rate: float = 0.002
    slippage_bps: int = 8
    min_order_amount: int = 50_000

    @classmethod
    def zero(cls) -> CostSettings:
        return cls(commission_rate=0.0, sell_fee_rate=0.0, slippage_bps=0, min_order_amount=0)


class UniverseSettings(BaseModel):
    segments: list[str] = Field(default_factory=lambda: ["KOSPI", "KOSDAQ"])
    liquidity_top_n: int = 200
    watch_top_n: int = 60
    min_trading_value: float = 3_000_000_000
    include_etf: bool = False
    excluded_warning_types: list[str] = Field(default_factory=list)
    # 미국 유니버스 전용: 기본 후보군과 S&P500 상장 목록 사용 여부
    candidate_symbols: list[str] = Field(default_factory=list)
    use_sp500_listing: bool = False
    pool_cap: int = 150


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
    # 고정 스탑은 변동성 큰 종목에서 노이즈 손절(churn)을 유발한다.
    # 실제 스탑 폭 = clamp(변동성 × multiple, 기본값(floor), max값(cap))
    stop_loss_pct: float = 0.04
    max_stop_loss_pct: float = 0.08
    stop_volatility_multiple: float = 2.0
    trailing_stop_pct: float = 0.03
    max_trailing_stop_pct: float = 0.06
    trailing_volatility_multiple: float = 2.0
    breakeven_trigger_pct: float = 0.025
    breakeven_buffer_pct: float = 0.003
    # 백테스트 스윕에서 KR은 이익잠금이 러너를 일찍 잘라 수익을 깎았다(+101%→+121%).
    # 사실상 비활성(100%)으로 두고, US 프로필만 낮은 트리거로 활성화한다.
    profit_lock_trigger_pct: float = 1.00
    profit_lock_trailing_stop_pct: float = 0.02
    daily_drop_exit_pct: float = 0.035
    # 스윕에서 10→15일이 우세: 추세를 못 만든 포지션만 정리하되 너무 일찍 자르지 않는다
    max_holding_days: int = 15
    # 비용 인지 게이트: 기대변동(일변동성×√보유일)이 왕복비용×배수 이상일 때만 진입
    min_edge_multiple: float = 3.0
    # 청산 후 같은 종목 재진입 금지 기간(수수료 회전 방지).
    # 백테스트 스윕에서 1일 → 5일이 전 구간 일관 개선 (손절 직후 재매수 churn 차단)
    reentry_cooldown_days: int = 5
    # 정규장 종료 N분 전 신규 진입 차단 (KR은 종가 단일가 시작이 우선 적용)
    entry_cutoff_minutes: int = 10

    @field_validator("momentum_weights")
    @classmethod
    def weights_must_match_windows(cls, value: list[float], info):
        windows = info.data.get("momentum_windows", [])
        if windows and len(value) != len(windows):
            raise ValueError("momentum_weights must match momentum_windows length")
        return value


class ExecutionSettings(BaseModel):
    max_entry_spread_bps: int = 25
    max_exit_spread_bps: int = 80
    max_chase_bps: int = 20
    max_orderbook_participation: float = 0.25
    price_limit_buffer_pct: float = 0.01
    stale_order_minutes: int = 3
    cancel_stale_orders: bool = True


class MarketProfile(BaseModel):
    enabled: bool = True
    universe: UniverseSettings = Field(default_factory=UniverseSettings)
    strategy: StrategySettings = Field(default_factory=StrategySettings)
    execution: ExecutionSettings = Field(default_factory=ExecutionSettings)
    costs: CostSettings = Field(default_factory=CostSettings)


def default_market_profiles() -> dict[str, dict]:
    """KR은 클래스 기본값(국내 튜닝), US는 높은 수수료를 전제로 한 저회전 프로필."""
    return {
        "KR": {},
        "US": {
            "universe": {
                "segments": ["NYSE", "NASDAQ", "AMEX"],
                "liquidity_top_n": 120,
                "watch_top_n": 30,
                "min_trading_value": 50_000_000,
                "candidate_symbols": list(DEFAULT_US_SYMBOLS),
                "excluded_warning_types": [],
            },
            "strategy": {
                "max_positions": 4,
                "min_20d_return_pct": 0.04,
                "min_60d_return_pct": 0.08,
                "max_5d_return_pct": 0.30,
                "max_drawdown_from_high_pct": 0.25,
                "max_distance_from_ma20_pct": 0.15,
                "max_gap_up_pct": 0.05,
                "max_intraday_extension_pct": 0.06,
                "volume_spike_multiplier": 1.8,
                "stop_loss_pct": 0.06,
                "max_stop_loss_pct": 0.10,
                "trailing_stop_pct": 0.05,
                "max_trailing_stop_pct": 0.08,
                "breakeven_trigger_pct": 0.04,
                "breakeven_buffer_pct": 0.004,
                "profit_lock_trigger_pct": 0.12,
                "profit_lock_trailing_stop_pct": 0.03,
                "daily_drop_exit_pct": 0.045,
                # 스윕에서 25→45일 연장이 회전 비용을 줄여 전·후반 모두 개선
                "max_holding_days": 45,
                "min_edge_multiple": 5.0,
                "reentry_cooldown_days": 10,
                "entry_cutoff_minutes": 30,
            },
            "execution": {
                "max_entry_spread_bps": 15,
                "max_exit_spread_bps": 50,
                "max_chase_bps": 10,
            },
            "costs": {
                "commission_rate": 0.0025,
                "sell_fee_rate": 0.00005,
                "slippage_bps": 5,
                "min_order_amount": 500,
            },
        },
    }


class RiskSettings(BaseModel):
    """계좌 단위 리스크 한도. 자산 평가와 한도 계산은 모두 원화 환산 기준."""

    max_symbol_weight: float = 0.18
    min_cash_weight: float = 0.10
    target_position_volatility_pct: float = 0.025
    max_entry_risk_pct: float = 0.008
    daily_loss_limit_pct: float = 0.03
    weekly_loss_limit_pct: float = 0.08
    max_drawdown_pct: float = 0.15
    max_live_order_amount_krw: int = 1_000_000
    min_paper_trading_days: int = 20
    paper_trading_days_completed: int = 0


class FxSettings(BaseModel):
    fallback_usd_krw: float = 1400.0
    refresh_minutes: int = 10


class ScheduleSettings(BaseModel):
    preflight_time: str = "08:30"
    premarket_report_time: str = "08:50"
    us_universe_refresh_time: str = "21:30"
    reconcile_interval_minutes: int = 5
    report_time: str = "15:40"


class PaperSettings(BaseModel):
    initial_cash_krw: int = 10_000_000
    initial_cash_usd: int = 7_000


class Settings(BaseModel):
    mode: RunMode = RunMode.PAPER
    timezone: str = "Asia/Seoul"
    database_url: str = "sqlite:///data/toss_bot.sqlite3"
    reports_dir: str = "reports"
    toss: TossSettings = Field(default_factory=TossSettings)
    markets: dict[str, MarketProfile] = Field(default_factory=dict, validate_default=True)
    risk: RiskSettings = Field(default_factory=RiskSettings)
    fx: FxSettings = Field(default_factory=FxSettings)
    schedule: ScheduleSettings = Field(default_factory=ScheduleSettings)
    paper: PaperSettings = Field(default_factory=PaperSettings)

    toss_client_id: str | None = None
    toss_client_secret: str | None = None
    toss_account_seq: int | None = None
    discord_webhook_url: str | None = None
    enable_live_trading: bool = False

    @field_validator("markets", mode="before")
    @classmethod
    def merge_market_defaults(cls, value: Any) -> dict:
        merged = default_market_profiles()
        for market, overrides in (value or {}).items():
            base = merged.get(str(market), {})
            merged[str(market)] = _deep_merge(base, overrides if isinstance(overrides, dict) else {})
        return merged

    def enabled_markets(self) -> list[MarketCountry]:
        return [
            MarketCountry(name)
            for name, profile in self.markets.items()
            if profile.enabled and name in MarketCountry.__members__
        ]

    def market_profile(self, market: MarketCountry | str) -> MarketProfile:
        return self.markets[str(market)]


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


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
