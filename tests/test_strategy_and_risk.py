from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from toss_bot.config import CostSettings, RiskSettings, StrategySettings
from toss_bot.models import Candle, Position, RankedCandidate, UniverseCandidate
from toss_bot.risk import RiskManager, RiskState
from toss_bot.strategy import HybridMomentumStrategy


def candle(index: int, close: str, volume: str = "100") -> Candle:
    value = Decimal(close)
    return Candle(
        timestamp=datetime(2026, 6, 10, 9, 0) + timedelta(minutes=index),
        open=value,
        high=value,
        low=value,
        close=value,
        volume=Decimal(volume),
    )


def test_entry_signal_requires_breakout_and_volume_spike():
    strategy = HybridMomentumStrategy(StrategySettings(intraday_box_minutes=3, volume_spike_multiplier=2.0))
    candidate = RankedCandidate("000001", "a", "KOSPI", Decimal("1"), Decimal("10"), Decimal("0.1"))
    daily = [candle(0, "95"), Candle(datetime(2026, 6, 9), Decimal("90"), Decimal("100"), Decimal("89"), Decimal("99"), Decimal("100"))]
    intraday = [candle(0, "96", "100"), candle(1, "97", "100"), candle(2, "98", "100"), candle(3, "101", "250")]

    signal = strategy.entry_signal(candidate, daily, intraday, Decimal("100000"))

    assert signal is not None
    assert signal.symbol == "000001"
    assert signal.quantity == Decimal("990")


def test_entry_signal_blocked_when_expected_move_cannot_cover_costs():
    # 왕복비용: 0.25%*2 + 0.005% + 5bps*2 = 0.605%, 허들 5배 = 3.025%
    # 변동성 0.4%/일 × sqrt(10일) ≈ 1.26% → 진입 차단
    us_costs = CostSettings(commission_rate=0.0025, sell_fee_rate=0.00005, slippage_bps=5, min_order_amount=0)
    strategy = HybridMomentumStrategy(
        StrategySettings(intraday_box_minutes=3, volume_spike_multiplier=2.0, min_edge_multiple=5.0, max_holding_days=10),
        us_costs,
    )
    low_vol = RankedCandidate("AAPL", "a", "NASDAQ", Decimal("1"), Decimal("10"), Decimal("0.004"))
    high_vol = RankedCandidate("NVDA", "b", "NASDAQ", Decimal("1"), Decimal("10"), Decimal("0.03"))
    daily = [candle(0, "95"), Candle(datetime(2026, 6, 9), Decimal("90"), Decimal("100"), Decimal("89"), Decimal("99"), Decimal("100"))]
    intraday = [candle(0, "96", "100"), candle(1, "97", "100"), candle(2, "98", "100"), candle(3, "101", "250")]

    assert strategy.entry_signal(low_vol, daily, intraday, Decimal("100000")) is None
    assert strategy.entry_signal(high_vol, daily, intraday, Decimal("100000")) is not None


def test_exit_signal_triggers_fixed_stop():
    strategy = HybridMomentumStrategy(StrategySettings(stop_loss_pct=0.04))
    position = Position("000001", Decimal("10"), Decimal("100"), date(2026, 6, 1), Decimal("110"))

    signal = strategy.exit_signal(position, [candle(0, "95")], date(2026, 6, 2))

    assert signal is not None
    assert signal.reason == "fixed stop loss"


def test_exit_signal_tightens_trailing_stop_after_profit_lock():
    strategy = HybridMomentumStrategy(
        StrategySettings(profit_lock_trigger_pct=0.08, profit_lock_trailing_stop_pct=0.02)
    )
    position = Position("000001", Decimal("10"), Decimal("100"), date(2026, 6, 1), Decimal("112"))

    signal = strategy.exit_signal(position, [candle(0, "109")], date(2026, 6, 2))

    assert signal is not None
    assert signal.reason == "profit lock trailing stop"


def test_breakeven_stop_covers_round_trip_costs():
    # breakeven_buffer 0.3%보다 왕복비용 0.605%가 크므로 본전 스탑은 비용까지 덮어야 한다.
    us_costs = CostSettings(commission_rate=0.0025, sell_fee_rate=0.00005, slippage_bps=5, min_order_amount=0)
    strategy = HybridMomentumStrategy(
        StrategySettings(
            breakeven_trigger_pct=0.025,
            breakeven_buffer_pct=0.003,
            trailing_stop_pct=0.10,
            stop_loss_pct=0.10,
            daily_drop_exit_pct=0.50,
            max_holding_days=100,
        ),
        us_costs,
    )
    position = Position("AAPL", Decimal("10"), Decimal("100"), date(2026, 6, 1), Decimal("104"))

    # 100.4: 버퍼(0.3%)는 넘었지만 왕복비용(0.605%) 미만 → 본전 보호 발동
    signal = strategy.exit_signal(position, [candle(0, "100.4")], date(2026, 6, 2))

    assert signal is not None
    assert signal.reason == "breakeven profit protect"


def test_risk_blocks_daily_loss_limit():
    state = RiskState(
        start_day_equity=Decimal("1000000"),
        start_week_equity=Decimal("1000000"),
        peak_equity=Decimal("1000000"),
        current_equity=Decimal("1000000"),
    )
    risk = RiskManager(RiskSettings(daily_loss_limit_pct=0.03), state)

    risk.update_equity(Decimal("969000"))

    allowed, reason = risk.can_enter("000001", Decimal("500000"), max_positions=8)
    assert not allowed
    assert reason == "daily loss limit reached"


def test_risk_counts_market_positions_separately():
    state = RiskState(
        start_day_equity=Decimal("1000000"),
        start_week_equity=Decimal("1000000"),
        peak_equity=Decimal("1000000"),
        current_equity=Decimal("1000000"),
    )
    positions = {
        "005930": Position("005930", Decimal("1"), Decimal("70000"), date(2026, 6, 1), Decimal("70000")),
        "AAPL": Position("AAPL", Decimal("1"), Decimal("180"), date(2026, 6, 1), Decimal("180")),
    }
    risk = RiskManager(RiskSettings(), state, positions)

    # 전체 포지션은 2개지만 US 시장 포지션은 1개뿐이므로 max 2에서 진입 가능해야 한다
    allowed, reason = risk.can_enter("MSFT", Decimal("500000"), max_positions=2, open_positions=1)
    assert allowed
    assert reason == "ok"


def test_rank_candidates_filters_salient_payoff():
    strategy = HybridMomentumStrategy(StrategySettings(min_score=0, max_5d_return_pct=0.20))
    universe = [UniverseCandidate("000001", "a", "KOSPI", Decimal("1000000000"), Decimal("1"), Decimal("1"))]
    candles = [candle(index, str(100 + index // 3)) for index in range(125)]
    candles[-1] = candle(124, "180")

    ranked = strategy.rank_candidates(universe, {"000001": candles})

    assert ranked == []


def test_risk_budget_scales_down_high_volatility_position():
    state = RiskState(
        start_day_equity=Decimal("1000000"),
        start_week_equity=Decimal("1000000"),
        peak_equity=Decimal("1000000"),
        current_equity=Decimal("1000000"),
    )
    risk = RiskManager(RiskSettings(max_symbol_weight=0.2, target_position_volatility_pct=0.02), state)

    budget = risk.position_budget(Decimal("1000000"), Decimal("0.10"))

    assert budget == Decimal("50000")


def test_risk_budget_caps_cash_by_entry_risk():
    state = RiskState(
        start_day_equity=Decimal("1000000"),
        start_week_equity=Decimal("1000000"),
        peak_equity=Decimal("1000000"),
        current_equity=Decimal("1000000"),
    )
    risk = RiskManager(
        RiskSettings(max_symbol_weight=0.5, min_cash_weight=0, max_entry_risk_pct=0.01),
        state,
    )

    budget = risk.position_budget(Decimal("1000000"), None, Decimal("0.05"))

    assert budget == Decimal("200000")
