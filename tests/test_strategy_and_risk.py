from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from toss_bot.config import CostSettings, RiskSettings, StrategySettings
from toss_bot.models import Candle, MarketCountry, Position, RankedCandidate, UniverseCandidate
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
    # 마지막 캔들은 거래량이 거의 없는 미완성 분봉: 돌파 확인은 직전 완성 분봉(거래량 250)으로 한다.
    intraday = [
        candle(0, "96", "100"),
        candle(1, "97", "100"),
        candle(2, "98", "100"),
        candle(3, "101", "250"),
        candle(4, "101", "10"),
    ]

    signal = strategy.entry_signal(candidate, daily, intraday, Decimal("100000"))

    assert signal is not None
    assert signal.symbol == "000001"
    assert signal.quantity == Decimal("990")


def test_entry_signal_confirms_on_completed_candle_not_partial():
    # 미완성 분봉(latest)의 수 초치 거래량으로 스파이크를 판정하면 진입이 사실상 불가능해진다.
    strategy = HybridMomentumStrategy(StrategySettings(intraday_box_minutes=3, volume_spike_multiplier=2.0))
    candidate = RankedCandidate("000001", "a", "KOSPI", Decimal("1"), Decimal("10"), Decimal("0.1"))
    daily = [candle(0, "95"), Candle(datetime(2026, 6, 9), Decimal("90"), Decimal("100"), Decimal("89"), Decimal("99"), Decimal("100"))]
    # 돌파 분봉(완성, 거래량 250) 직후 미완성 분봉이 돌파선 아래로 되밀리면 진입하지 않는다
    pulled_back = [
        candle(0, "96", "100"),
        candle(1, "97", "100"),
        candle(2, "98", "100"),
        candle(3, "101", "250"),
        candle(4, "99", "10"),
    ]

    assert strategy.entry_signal(candidate, daily, pulled_back, Decimal("100000")) is None


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
    intraday = [
        candle(0, "96", "100"),
        candle(1, "97", "100"),
        candle(2, "98", "100"),
        candle(3, "101", "250"),
        candle(4, "101", "10"),
    ]

    assert strategy.entry_signal(low_vol, daily, intraday, Decimal("100000")) is None
    assert strategy.entry_signal(high_vol, daily, intraday, Decimal("100000")) is not None


def test_us_entry_limit_price_keeps_cents():
    # money()로 달러를 정수 절사하면 chase 한도 계산이 틀어져 미국 매수가 대부분 거절된다.
    strategy = HybridMomentumStrategy(
        StrategySettings(intraday_box_minutes=3, volume_spike_multiplier=2.0),
        CostSettings.zero(),
        MarketCountry.US,
    )
    candidate = RankedCandidate("AAPL", "a", "NASDAQ", Decimal("1"), Decimal("10"), Decimal("0.1"))
    daily = [candle(0, "95"), Candle(datetime(2026, 6, 9), Decimal("90"), Decimal("100"), Decimal("89"), Decimal("99"), Decimal("100"))]
    intraday = [
        candle(0, "96", "100"),
        candle(1, "97", "100"),
        candle(2, "98", "100"),
        candle(3, "101.37", "250"),
        candle(4, "101.37", "10"),
    ]

    signal = strategy.entry_signal(candidate, daily, intraday, Decimal("100000"))

    assert signal is not None
    assert signal.limit_price == Decimal("101.37")


def test_entry_signal_ignores_previous_session_candles():
    # 장 초반에는 분봉 조회 결과 대부분이 전일 데이터라 박스/VWAP이 오염된다.
    strategy = HybridMomentumStrategy(StrategySettings(intraday_box_minutes=3, volume_spike_multiplier=2.0))
    candidate = RankedCandidate("000001", "a", "KOSPI", Decimal("1"), Decimal("10"), Decimal("0.1"))
    daily = [candle(0, "95"), Candle(datetime(2026, 6, 9), Decimal("90"), Decimal("100"), Decimal("89"), Decimal("99"), Decimal("100"))]
    previous_session = [
        Candle(datetime(2026, 6, 9, 15, 19) + timedelta(minutes=index), Decimal("200"), Decimal("200"), Decimal("200"), Decimal("200"), Decimal("100"))
        for index in range(5)
    ]
    intraday = previous_session + [
        candle(0, "96", "100"),
        candle(1, "97", "100"),
        candle(2, "98", "100"),
        candle(3, "101", "250"),
        candle(4, "101", "10"),
    ]

    signal = strategy.entry_signal(candidate, daily, intraday, Decimal("100000"))

    # 전일 고가 200이 박스에 섞이면 돌파가 불가능해진다. 세션 절단 후에는 진입돼야 한다.
    assert signal is not None


def test_exit_daily_drop_uses_current_session_open():
    settings = StrategySettings(
        daily_drop_exit_pct=0.035,
        stop_loss_pct=0.5,
        trailing_stop_pct=0.5,
        breakeven_trigger_pct=9.9,
        profit_lock_trigger_pct=9.9,
        max_holding_days=100,
    )
    strategy = HybridMomentumStrategy(settings)
    position = Position("000001", Decimal("10"), Decimal("100"), date(2026, 6, 9), Decimal("100"))
    previous_session = [
        Candle(datetime(2026, 6, 9, 15, 20), Decimal("110"), Decimal("110"), Decimal("110"), Decimal("110"), Decimal("100"))
    ]
    today_session = [
        Candle(datetime(2026, 6, 10, 9, 0), Decimal("100"), Decimal("100"), Decimal("99"), Decimal("100"), Decimal("100")),
        Candle(datetime(2026, 6, 10, 9, 1), Decimal("100"), Decimal("100"), Decimal("99"), Decimal("99"), Decimal("100")),
    ]

    # 전일 시가 110 기준이면 -10%로 오발동, 당일 시가 100 기준이면 -1%로 미발동이 맞다.
    signal = strategy.exit_signal(position, previous_session + today_session, date(2026, 6, 10))

    assert signal is None


def test_exit_signal_trails_from_session_high():
    settings = StrategySettings(
        trailing_stop_pct=0.03,
        stop_loss_pct=0.5,
        daily_drop_exit_pct=0.5,
        breakeven_trigger_pct=9.9,
        profit_lock_trigger_pct=9.9,
        max_holding_days=100,
    )
    strategy = HybridMomentumStrategy(settings)
    position = Position("000001", Decimal("10"), Decimal("100"), date(2026, 6, 9), Decimal("100"))
    intraday = [
        Candle(datetime(2026, 6, 10, 9, 0), Decimal("100"), Decimal("120"), Decimal("100"), Decimal("118"), Decimal("100")),
        Candle(datetime(2026, 6, 10, 9, 1), Decimal("118"), Decimal("118"), Decimal("116"), Decimal("116"), Decimal("100")),
    ]

    # 세션 고가 120 기준 트레일링 스탑 116.4 → 마지막 분봉 고가(116)만 보면 놓친다.
    signal = strategy.exit_signal(position, intraday, date(2026, 6, 10))

    assert signal is not None
    assert signal.reason == "trailing stop"


def test_rank_allows_old_spike_outside_recent_window():
    # 과거(한 달 이전) 급등 이력만으로 강한 모멘텀 종목을 배제하면 후보가 사라진다.
    strategy = HybridMomentumStrategy(StrategySettings(min_score=0, max_5d_return_pct=0.25))
    universe = [UniverseCandidate("000001", "a", "KOSPI", Decimal("100000000000"), Decimal("1"), Decimal("1"))]
    closes = [Decimal(100 + index) for index in range(130)]
    for index in range(20, 25):
        closes[index] = Decimal("150")  # 옛 급등 구간 (5일 +30%)
    candles = [candle(index, str(closes[index])) for index in range(130)]

    ranked = strategy.rank_candidates(universe, {"000001": candles})

    assert [item.symbol for item in ranked] == ["000001"]


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


def test_max_holding_days_spares_locked_winner():
    settings = StrategySettings(
        profit_lock_trigger_pct=0.08,
        profit_lock_trailing_stop_pct=0.02,
        max_holding_days=10,
        stop_loss_pct=0.5,
        daily_drop_exit_pct=0.5,
        breakeven_trigger_pct=9.9,
    )
    strategy = HybridMomentumStrategy(settings)
    winner = Position("000001", Decimal("10"), Decimal("100"), date(2026, 5, 1), Decimal("115"))
    laggard = Position("000002", Decimal("10"), Decimal("100"), date(2026, 5, 1), Decimal("103"))

    # 고점 +15% 승자는 트레일링(112.7)이 관리하므로 40일째에도 시간 청산하지 않는다
    assert strategy.exit_signal(winner, [candle(0, "114")], date(2026, 6, 10)) is None
    laggard_signal = strategy.exit_signal(laggard, [candle(0, "102")], date(2026, 6, 10))
    assert laggard_signal is not None
    assert laggard_signal.reason == "max holding days"


def test_risk_off_exits_losers_but_trails_winners():
    settings = StrategySettings(
        trailing_stop_pct=0.05,
        profit_lock_trailing_stop_pct=0.02,
        profit_lock_trigger_pct=0.20,
        stop_loss_pct=0.5,
        daily_drop_exit_pct=0.5,
        breakeven_trigger_pct=9.9,
        max_holding_days=100,
    )
    strategy = HybridMomentumStrategy(settings)
    loser = Position("000001", Decimal("10"), Decimal("100"), date(2026, 6, 9), Decimal("100"))
    winner = Position("000002", Decimal("10"), Decimal("100"), date(2026, 6, 9), Decimal("110"))

    loser_signal = strategy.exit_signal(loser, [candle(0, "99")], date(2026, 6, 10), market_filter_ok=False)
    assert loser_signal is not None
    assert loser_signal.reason == "market filter risk-off"

    # 수익 포지션은 즉시 청산하지 않되 트레일을 2%로 조인다: 110 고점 → 107.8 아래면 청산
    assert strategy.exit_signal(winner, [candle(0, "109")], date(2026, 6, 10), market_filter_ok=False) is None
    tightened = strategy.exit_signal(winner, [candle(0, "107")], date(2026, 6, 10), market_filter_ok=False)
    assert tightened is not None
    assert tightened.reason == "risk-off tightened trailing stop"


def test_exit_stop_widens_with_volatility():
    settings = StrategySettings(
        stop_loss_pct=0.04,
        max_stop_loss_pct=0.08,
        stop_volatility_multiple=2.5,
        trailing_stop_pct=0.03,
        max_trailing_stop_pct=0.06,
        trailing_volatility_multiple=2.0,
        breakeven_trigger_pct=9.9,
        profit_lock_trigger_pct=9.9,
        daily_drop_exit_pct=0.5,
        max_holding_days=100,
    )
    strategy = HybridMomentumStrategy(settings)
    position = Position("000001", Decimal("10"), Decimal("100"), date(2026, 6, 9), Decimal("100"))

    # 변동성 정보가 없으면 기존 고정 스탑(4%) 그대로: 95.5에서 손절
    no_vol = strategy.exit_signal(position, [candle(0, "95.5")], date(2026, 6, 10))
    assert no_vol is not None
    assert no_vol.reason == "fixed stop loss"

    # 일변동성 3% 종목은 스탑이 7.5%로 넓어져 같은 -4.5%에서 버틴다 (노이즈 손절 방지)
    assert (
        strategy.exit_signal(position, [candle(0, "95.5")], date(2026, 6, 10), daily_volatility=Decimal("0.03"))
        is None
    )


def test_exit_stop_capped_at_max_even_for_extreme_volatility():
    settings = StrategySettings(
        stop_loss_pct=0.04,
        max_stop_loss_pct=0.08,
        stop_volatility_multiple=2.5,
        trailing_stop_pct=0.5,
        max_trailing_stop_pct=0.5,
        breakeven_trigger_pct=9.9,
        profit_lock_trigger_pct=9.9,
        daily_drop_exit_pct=0.5,
        max_holding_days=100,
    )
    strategy = HybridMomentumStrategy(settings)
    position = Position("000001", Decimal("10"), Decimal("100"), date(2026, 6, 9), Decimal("100"))

    # 변동성 10%여도 스탑은 cap(8%)까지만 넓어진다: 92 이하에서는 반드시 손절
    capped = strategy.exit_signal(position, [candle(0, "91.9")], date(2026, 6, 10), daily_volatility=Decimal("0.10"))
    assert capped is not None
    assert capped.reason == "fixed stop loss"
    assert (
        strategy.exit_signal(position, [candle(0, "92.1")], date(2026, 6, 10), daily_volatility=Decimal("0.10"))
        is None
    )


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
