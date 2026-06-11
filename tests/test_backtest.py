from __future__ import annotations

from decimal import Decimal

import pandas as pd

from toss_bot.backtest import Backtester
from toss_bot.config import Settings


def make_close_frame(periods: int = 280) -> pd.DataFrame:
    index = pd.bdate_range("2025-05-01", periods=periods)
    data = {
        # 추세 강도가 다른 상승 종목들: 랭킹과 매수가 일어나야 한다
        "AAA": [100 + 0.8 * step for step in range(periods)],
        "BBB": [100 + 0.6 * step for step in range(periods)],
        "CCC": [100 + 0.4 * step for step in range(periods)],
    }
    return pd.DataFrame(data, index=index)


def kr_strategy(settings: Settings, **overrides):
    # 합성 데이터는 변동성이 거의 0이라 비용 허들에 막히므로, 허들이 주제가 아닌
    # 테스트에서는 min_edge_multiple을 끈다.
    overrides.setdefault("min_edge_multiple", 0)
    return settings.market_profile("KR").strategy.model_copy(update=overrides)


def test_rotation_backtest_trades_in_short_window():
    # 룩백 데이터가 함께 로드되므로 6개월 미만 백테스트에서도 거래가 나와야 한다.
    settings = Settings()
    backtester = Backtester(settings)
    closes = make_close_frame()
    start = closes.index[200].date()
    end = closes.index[-1].date()
    profile = settings.market_profile("KR")

    result = backtester._rotation_backtest(
        {"close": closes}, start, end, kr_strategy(settings), profile.costs, Decimal("10000000"), "KRW"
    )

    assert result.trades > 0
    assert result.end_equity > 0


def test_rotation_backtest_rebalances_weekly_not_once():
    settings = Settings()
    backtester = Backtester(settings)
    closes = make_close_frame()
    profile = settings.market_profile("KR")
    rebalance_days = []
    original_rank = backtester._rank_from_close_frame

    def tracking_rank(frame, strategy_settings):
        rebalance_days.append(frame.index[-1].date())
        return original_rank(frame, strategy_settings)

    backtester._rank_from_close_frame = tracking_rank
    start = closes.index[200].date()
    end = closes.index[-1].date()

    backtester._rotation_backtest(
        {"close": closes}, start, end, kr_strategy(settings), profile.costs, Decimal("10000000"), "KRW"
    )

    # 280-200=80 거래일 ≈ 16주: 주당 한 번 리밸런스 평가가 일어나야 한다
    assert len(rebalance_days) >= 10
    assert len(set(day.isocalendar()[:2] for day in rebalance_days)) == len(rebalance_days)


def test_rotation_backtest_applies_stop_loss():
    # 진입 후 급락하는 종목은 고정 손절로 빠져나와 계좌가 보호돼야 한다.
    settings = Settings()
    backtester = Backtester(settings)
    periods = 280
    index = pd.bdate_range("2025-05-01", periods=periods)
    prices = [100 + 0.5 * step for step in range(201)]
    crash_start = prices[-1]
    for step in range(periods - 201):
        prices.append(crash_start * (0.97 ** (step + 1)))
    closes = pd.DataFrame({"AAA": prices}, index=index)
    profile = settings.market_profile("KR")
    start = closes.index[200].date()
    end = closes.index[-1].date()

    result = backtester._rotation_backtest(
        {"close": closes}, start, end, kr_strategy(settings), profile.costs, Decimal("10000000"), "KRW"
    )

    # 매수 1건 + 손절 매도 1건 이상, 손실은 포지션 비중 × 손절폭 수준에 그쳐야 한다
    assert result.trades >= 2
    assert result.end_equity > Decimal("10000000") * Decimal("0.97")


def test_rotation_backtest_lets_locked_winner_run_past_max_holding():
    # 이익 보호 구간에 도달한 승자는 max_holding_days에 강제 청산되지 않는다.
    settings = Settings()
    backtester = Backtester(settings)
    periods = 280
    index = pd.bdate_range("2025-05-01", periods=periods)
    # 진입 후 max_holding_days(10일) 안에 profit lock(8%)을 넘길 만큼 가파르게 상승하는 종목
    prices = [100 + 0.5 * step for step in range(201)]
    last = prices[-1]
    for step in range(periods - 201):
        prices.append(last * (1.015 ** (step + 1)))
    closes = pd.DataFrame({"AAA": prices}, index=index)
    profile = settings.market_profile("KR")
    start = closes.index[200].date()
    end = closes.index[-1].date()

    result = backtester._rotation_backtest(
        {"close": closes},
        start,
        end,
        kr_strategy(settings, profit_lock_trigger_pct=0.08),
        profile.costs,
        Decimal("10000000"),
        "KRW",
    )

    # 시간 청산이 없으니 매수 1건만 존재해야 한다 (계속 보유)
    assert result.trades == 1


def test_rotation_backtest_blocks_low_volatility_entries_by_edge_gate():
    # 기대변동이 왕복비용 허들에 못 미치는 저변동 종목은 사지 않는다 (실전 entry_signal과 동일).
    settings = Settings()
    backtester = Backtester(settings)
    closes = make_close_frame()
    profile = settings.market_profile("KR")
    start = closes.index[200].date()
    end = closes.index[-1].date()

    result = backtester._rotation_backtest(
        {"close": closes}, start, end, profile.strategy, profile.costs, Decimal("10000000"), "KRW"
    )

    # 선형 상승 합성 데이터의 일변동성 ≈ 0 → 비용 허들이 전부 차단
    assert result.trades == 0


def test_rotation_backtest_regime_filter_blocks_entries_in_downtrend():
    # 유니버스 동일가중 지수가 MA60 아래면 신규 진입을 멈춘다.
    settings = Settings()
    backtester = Backtester(settings)
    periods = 280
    index = pd.bdate_range("2025-05-01", periods=periods)
    data = {"WIN": [100 + 0.8 * step for step in range(periods)]}
    # 지수를 끌어내리는 하락 종목들: 150일째부터 매일 1%씩 하락
    for column in ("L1", "L2", "L3", "L4", "L5", "L6", "L7"):
        prices = [100 + 0.3 * step for step in range(150)]
        last = prices[-1]
        for step in range(periods - 150):
            prices.append(last * (0.99 ** (step + 1)))
        data[column] = prices
    closes = pd.DataFrame(data, index=index)
    profile = settings.market_profile("KR")
    start = closes.index[200].date()
    end = closes.index[-1].date()

    result = backtester._rotation_backtest(
        {"close": closes}, start, end, kr_strategy(settings), profile.costs, Decimal("10000000"), "KRW"
    )

    # WIN은 랭킹을 통과하지만 레짐 필터가 모든 진입을 막아야 한다
    assert result.trades == 0
