from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_DOWN

import pandas as pd

from .config import CostSettings, Settings, StrategySettings
from .models import Candle, MarketCountry, UniverseCandidate
from .strategy import HybridMomentumStrategy
from .utils import dec, money, quiet_external_data_source


@dataclass(frozen=True)
class BacktestResult:
    start: date
    end: date
    start_equity: Decimal
    end_equity: Decimal
    total_return: Decimal
    trades: int
    method: str
    currency: str = "KRW"
    warning: str | None = None


class Backtester:
    def __init__(self, settings: Settings):
        self.settings = settings

    def run(self, start: date, end: date, market: MarketCountry | str = MarketCountry.KR) -> BacktestResult:
        market = MarketCountry(market)
        profile = self.settings.market_profile(market)
        errors: list[str] = []
        if market == MarketCountry.KR:
            loaders = [("KRX", self._load_kr_closes_krx), ("FinanceDataReader", self._load_kr_closes_fdr)]
            initial = Decimal(self.settings.paper.initial_cash_krw)
            currency = "KRW"
        else:
            loaders = [("FinanceDataReader", self._load_us_closes_fdr)]
            initial = Decimal(self.settings.paper.initial_cash_usd)
            currency = "USD"
        for name, loader in loaders:
            try:
                with quiet_external_data_source():
                    closes = loader(start, end)
                return self._rotation_backtest(
                    closes, start, end, profile.strategy, profile.costs, initial, currency
                )
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        return self._fallback_cost_smoke(start, end, profile.costs, initial, currency, "; ".join(errors))

    # --- 데이터 로더 ---------------------------------------------------------

    def _load_kr_closes_krx(self, start: date, end: date) -> pd.DataFrame:
        from pykrx import stock

        profile = self.settings.market_profile(MarketCountry.KR)
        lookback_start = start - timedelta(days=260)
        symbols: list[str] = []
        date_text = end.strftime("%Y%m%d")
        for segment in profile.universe.segments:
            frame = stock.get_market_ohlcv(date_text, market=segment)
            if frame.empty:
                continue
            filtered = frame[frame["거래대금"] >= profile.universe.min_trading_value]
            top = filtered.sort_values("거래대금", ascending=False).head(profile.universe.watch_top_n)
            symbols.extend(str(symbol) for symbol in top.index)
        symbols = symbols[: profile.universe.watch_top_n]
        if not symbols:
            raise RuntimeError("No KRX symbols for backtest")
        series = {}
        for symbol in symbols:
            frame = stock.get_market_ohlcv_by_date(
                lookback_start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), symbol
            )
            if frame.empty or "종가" not in frame:
                continue
            series[symbol] = frame["종가"]
        if not series:
            raise RuntimeError("No close history for backtest")
        return pd.DataFrame(series)

    def _load_kr_closes_fdr(self, start: date, end: date) -> pd.DataFrame:
        import FinanceDataReader as fdr

        profile = self.settings.market_profile(MarketCountry.KR)
        listing = fdr.StockListing("KRX")
        if listing.empty:
            raise RuntimeError("FinanceDataReader returned no KRX listing")
        market_column = "Market" if "Market" in listing.columns else "MarketId"
        listing = listing[listing[market_column].isin(profile.universe.segments)]
        if "Amount" in listing.columns:
            listing = listing.sort_values("Amount", ascending=False)
        symbols = [str(code).zfill(6) for code in listing["Code"].head(profile.universe.watch_top_n)]
        return self._load_fdr_frame(fdr, symbols, start - timedelta(days=260), end)

    def _load_us_closes_fdr(self, start: date, end: date) -> pd.DataFrame:
        import FinanceDataReader as fdr

        profile = self.settings.market_profile(MarketCountry.US)
        symbols = [
            symbol.replace(".", "-")  # FDR(야후 계열)은 BRK.B 대신 BRK-B 표기를 쓴다
            for symbol in profile.universe.candidate_symbols[: profile.universe.watch_top_n * 2]
        ]
        if not symbols:
            raise RuntimeError("No US candidate symbols configured for backtest")
        return self._load_fdr_frame(fdr, symbols, start - timedelta(days=260), end)

    def _load_fdr_frame(self, fdr, symbols: list[str], start: date, end: date) -> pd.DataFrame:
        series = {}
        for symbol in symbols:
            try:
                frame = fdr.DataReader(symbol, start.isoformat(), end.isoformat())
            except Exception:
                continue
            if frame.empty or "Close" not in frame:
                continue
            series[symbol] = frame["Close"]
        if not series:
            raise RuntimeError("No FinanceDataReader close history for backtest")
        return pd.DataFrame(series)

    # --- 시뮬레이션 ----------------------------------------------------------

    def _rotation_backtest(
        self,
        closes: pd.DataFrame,
        start: date,
        end: date,
        strategy_settings: StrategySettings,
        costs: CostSettings,
        initial: Decimal,
        currency: str,
    ) -> BacktestResult:
        closes = closes.dropna(axis=1, thresh=140).ffill()
        trading_days = [day.date() for day in closes.index if start <= day.date() <= end]
        if not trading_days:
            raise RuntimeError("No trading days for backtest")

        cash = initial
        holdings: dict[str, Decimal] = {}
        trades = 0
        max_window = max(strategy_settings.momentum_windows)

        for idx, day in enumerate(trading_days):
            timestamp = pd.Timestamp(day)
            if idx < max_window or (timestamp.weekday() != 0 and idx != max_window):
                continue
            prices = closes.loc[:timestamp].tail(max_window + 1)
            ranked = self._rank_from_close_frame(prices, strategy_settings)
            selected = ranked[: strategy_settings.max_positions]
            if not selected:
                continue
            current_prices = closes.loc[timestamp]
            equity = self._equity(cash, holdings, current_prices)

            for symbol in list(holdings):
                if symbol not in selected:
                    price = dec(current_prices[symbol])
                    cash += self._sell_value(holdings.pop(symbol), price, costs)
                    trades += 1

            target_weight = min(
                dec(self.settings.risk.max_symbol_weight),
                (Decimal("1") - dec(self.settings.risk.min_cash_weight)) / Decimal(len(selected)),
            )
            target_value = equity * target_weight
            for symbol in selected:
                price = dec(current_prices[symbol])
                if price <= 0 or symbol in holdings:
                    continue
                quantity = (target_value / price).to_integral_value(rounding=ROUND_DOWN)
                total_cost = self._buy_cost(quantity, price, costs)
                if quantity > 0 and total_cost <= cash:
                    cash -= total_cost
                    holdings[symbol] = quantity
                    trades += 1

        final_prices = closes.loc[pd.Timestamp(trading_days[-1])]
        end_equity = money(self._equity(cash, holdings, final_prices))
        return BacktestResult(
            start=start,
            end=end,
            start_equity=initial,
            end_equity=end_equity,
            total_return=(end_equity / initial) - Decimal("1"),
            trades=trades,
            method="daily_proxy_with_live_ranking",
            currency=currency,
            warning="Proxy backtest: intraday breakout, orderbook execution, stops, and session policy are not simulated.",
        )

    def _fallback_cost_smoke(
        self,
        start: date,
        end: date,
        costs: CostSettings,
        initial: Decimal,
        currency: str,
        error_summary: str = "",
    ) -> BacktestResult:
        round_trip_cost = dec(costs.commission_rate) * Decimal("2")
        round_trip_cost += dec(costs.sell_fee_rate)
        round_trip_cost += (dec(costs.slippage_bps) / Decimal("10000")) * Decimal("2")
        conservative_drag = initial * round_trip_cost
        end_equity = money(initial - conservative_drag)
        return BacktestResult(
            start=start,
            end=end,
            start_equity=initial,
            end_equity=end_equity,
            total_return=(end_equity / initial) - Decimal("1"),
            trades=2,
            method="cost_smoke",
            currency=currency,
            warning=f"Historical data backtest unavailable; returned cost-only smoke result. {error_summary}".strip(),
        )

    def _rank_from_close_frame(self, closes: pd.DataFrame, strategy_settings: StrategySettings) -> list[str]:
        strategy = HybridMomentumStrategy(strategy_settings)
        universe: list[UniverseCandidate] = []
        daily: dict[str, list[Candle]] = {}
        for symbol in closes.columns:
            values = closes[symbol].dropna()
            if len(values) < max(strategy_settings.momentum_windows) + 1:
                continue
            candles: list[Candle] = []
            for timestamp, raw_price in values.items():
                price = dec(raw_price)
                if price <= 0:
                    continue
                candles.append(Candle(pd.Timestamp(timestamp).to_pydatetime(), price, price, price, price, Decimal("1")))
            if len(candles) < max(strategy_settings.momentum_windows) + 1:
                continue
            daily[symbol] = candles
            universe.append(
                UniverseCandidate(
                    symbol=symbol,
                    name=symbol,
                    market="KOSPI",
                    trading_value=Decimal("100000000000"),
                    close=candles[-1].close,
                    volume=Decimal("1"),
                )
            )
        return [candidate.symbol for candidate in strategy.rank_candidates(universe, daily)]

    def _equity(self, cash: Decimal, holdings: dict[str, Decimal], prices: pd.Series) -> Decimal:
        equity = cash
        for symbol, quantity in holdings.items():
            equity += quantity * dec(prices[symbol])
        return equity

    def _buy_cost(self, quantity: Decimal, price: Decimal, costs: CostSettings) -> Decimal:
        gross = quantity * self._slipped(price, costs, buy=True)
        return gross + gross * dec(costs.commission_rate)

    def _sell_value(self, quantity: Decimal, price: Decimal, costs: CostSettings) -> Decimal:
        gross = quantity * self._slipped(price, costs, buy=False)
        commission = gross * dec(costs.commission_rate)
        fee = gross * dec(costs.sell_fee_rate)
        return gross - commission - fee

    def _slipped(self, price: Decimal, costs: CostSettings, buy: bool) -> Decimal:
        slip = dec(costs.slippage_bps) / Decimal("10000")
        return price * (Decimal("1") + slip if buy else Decimal("1") - slip)
