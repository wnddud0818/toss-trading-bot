"""스탑 파라미터 후보를 실데이터 백테스트로 비교한다.

사용: python scripts/param_sweep.py [KR|US]
데이터는 한 번만 내려받고, 전체 구간과 전·후반 분할 구간 성과를 함께 출력한다.
"""
from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from itertools import product

from toss_bot.backtest import Backtester
from toss_bot.config import load_settings
from toss_bot.models import MarketCountry
from toss_bot.utils import quiet_external_data_source

START = date(2026, 1, 2)
MID = date(2026, 3, 20)
END = date(2026, 6, 1)

GRIDS = {
    "KR": {
        "trailing_stop_pct": [0.03, 0.04, 0.05],
        "profit_lock_trailing_stop_pct": [0.02, 0.03],
        "reentry_cooldown_days": [1, 5, 10],
    },
    "US": {
        "trailing_stop_pct": [0.05, 0.07],
        "profit_lock_trailing_stop_pct": [0.03, 0.04],
        "reentry_cooldown_days": [5, 10],
    },
}


def main() -> None:
    market = MarketCountry(sys.argv[1] if len(sys.argv) > 1 else "KR")
    settings = load_settings("config/settings.yaml")
    backtester = Backtester(settings)
    profile = settings.market_profile(market)
    if market == MarketCountry.KR:
        loaders = [backtester._load_kr_closes_krx, backtester._load_kr_closes_fdr]
        initial = Decimal(settings.paper.initial_cash_krw)
        currency = "KRW"
    else:
        loaders = [backtester._load_us_closes_fdr]
        initial = Decimal(settings.paper.initial_cash_usd)
        currency = "USD"
    frames = None
    for loader in loaders:
        try:
            with quiet_external_data_source():
                frames = loader(START, END)
            break
        except Exception as exc:
            print(f"loader {loader.__name__} failed: {exc}")
    if frames is None:
        raise SystemExit("no data source available")

    grid = GRIDS[str(market)]
    keys = list(grid)
    print(f"{market} sweep: {' | '.join(keys)} -> full / first-half / second-half return (trades)")
    rows = []
    for values in product(*(grid[key] for key in keys)):
        overrides = dict(zip(keys, values))
        strategy_settings = profile.strategy.model_copy(update=overrides)
        results = []
        for window_start, window_end in ((START, END), (START, MID), (MID, END)):
            result = backtester._rotation_backtest(
                frames, window_start, window_end, strategy_settings, profile.costs, initial, currency
            )
            results.append(result)
        label = " | ".join(f"{value:.2f}" for value in values)
        rows.append((results[0].total_return, label, results))
        print(
            f"  {label} -> {results[0].total_return:8.4%} / {results[1].total_return:8.4%} / "
            f"{results[2].total_return:8.4%}  (trades {results[0].trades})"
        )
    rows.sort(reverse=True)
    print("\nTop 3 by full-period return:")
    for total, label, results in rows[:3]:
        print(f"  {label}: {total:.4%}")


if __name__ == "__main__":
    main()
