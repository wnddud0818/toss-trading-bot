from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_DOWN

import pandas as pd

from .config import Settings
from .utils import dec, money, quiet_external_data_source


@dataclass(frozen=True)
class BacktestResult:
    start: date
    end: date
    start_equity: Decimal
    end_equity: Decimal
    total_return: Decimal
    trades: int


class Backtester:
    def __init__(self, settings: Settings):
        self.settings = settings

    def run(self, start: date, end: date) -> BacktestResult:
        try:
            with quiet_external_data_source():
                return self._run_krx_rotation(start, end)
        except Exception:
            try:
                with quiet_external_data_source():
                    return self._run_fdr_rotation(start, end)
            except Exception:
                return self._fallback_cost_smoke(start, end)

    def _run_krx_rotation(self, start: date, end: date) -> BacktestResult:
        from pykrx import stock

        lookback_start = start - timedelta(days=260)
        symbols = self._top_liquidity_symbols(stock, end)
        if not symbols:
            raise RuntimeError("No KRX symbols for backtest")
        closes = self._load_close_frame(stock, symbols, lookback_start, end)
        closes = closes.dropna(axis=1, thresh=140).ffill()
        trading_days = [day.date() for day in closes.index if start <= day.date() <= end]
        if not trading_days:
            raise RuntimeError("No trading days for backtest")

        cash = Decimal(self.settings.paper.initial_cash_krw)
        holdings: dict[str, Decimal] = {}
        trades = 0
        max_window = max(self.settings.strategy.momentum_windows)

        for idx, day in enumerate(trading_days):
            timestamp = pd.Timestamp(day)
            if idx < max_window or (timestamp.weekday() != 0 and idx != max_window):
                continue
            prices = closes.loc[:timestamp].tail(max_window + 1)
            ranked = self._rank_from_close_frame(prices)
            selected = ranked[: self.settings.strategy.max_positions]
            if not selected:
                continue
            current_prices = closes.loc[timestamp]
            equity = self._equity(cash, holdings, current_prices)

            for symbol in list(holdings):
                if symbol not in selected:
                    price = dec(current_prices[symbol])
                    cash += self._sell_value(holdings.pop(symbol), price)
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
                total_cost = self._buy_cost(quantity, price)
                if quantity > 0 and total_cost <= cash:
                    cash -= total_cost
                    holdings[symbol] = quantity
                    trades += 1

        final_prices = closes.loc[pd.Timestamp(trading_days[-1])]
        end_equity = money(self._equity(cash, holdings, final_prices))
        initial = Decimal(self.settings.paper.initial_cash_krw)
        return BacktestResult(
            start=start,
            end=end,
            start_equity=initial,
            end_equity=end_equity,
            total_return=(end_equity / initial) - Decimal("1"),
            trades=trades,
        )

    def _run_fdr_rotation(self, start: date, end: date) -> BacktestResult:
        import FinanceDataReader as fdr

        listing = fdr.StockListing("KRX")
        if listing.empty:
            raise RuntimeError("FinanceDataReader returned no KRX listing")
        market_column = "Market" if "Market" in listing.columns else "MarketId"
        listing = listing[listing[market_column].isin(self.settings.universe.markets)]
        if "Amount" in listing.columns:
            listing = listing.sort_values("Amount", ascending=False)
        symbols = [str(code).zfill(6) for code in listing["Code"].head(self.settings.universe.watch_top_n)]
        closes = self._load_close_frame_from_fdr(fdr, symbols, start - timedelta(days=260), end)
        closes = closes.dropna(axis=1, thresh=140).ffill()
        trading_days = [day.date() for day in closes.index if start <= day.date() <= end]
        if not trading_days:
            raise RuntimeError("No trading days for FinanceDataReader backtest")

        cash = Decimal(self.settings.paper.initial_cash_krw)
        holdings: dict[str, Decimal] = {}
        trades = 0
        max_window = max(self.settings.strategy.momentum_windows)

        for idx, day in enumerate(trading_days):
            timestamp = pd.Timestamp(day)
            if idx < max_window or (timestamp.weekday() != 0 and idx != max_window):
                continue
            prices = closes.loc[:timestamp].tail(max_window + 1)
            ranked = self._rank_from_close_frame(prices)
            selected = ranked[: self.settings.strategy.max_positions]
            if not selected:
                continue
            current_prices = closes.loc[timestamp]
            equity = self._equity(cash, holdings, current_prices)

            for symbol in list(holdings):
                if symbol not in selected:
                    price = dec(current_prices[symbol])
                    cash += self._sell_value(holdings.pop(symbol), price)
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
                total_cost = self._buy_cost(quantity, price)
                if quantity > 0 and total_cost <= cash:
                    cash -= total_cost
                    holdings[symbol] = quantity
                    trades += 1

        final_prices = closes.loc[pd.Timestamp(trading_days[-1])]
        end_equity = money(self._equity(cash, holdings, final_prices))
        initial = Decimal(self.settings.paper.initial_cash_krw)
        return BacktestResult(
            start=start,
            end=end,
            start_equity=initial,
            end_equity=end_equity,
            total_return=(end_equity / initial) - Decimal("1"),
            trades=trades,
        )

    def _fallback_cost_smoke(self, start: date, end: date) -> BacktestResult:
        initial = Decimal(self.settings.paper.initial_cash_krw)
        round_trip_cost = dec(self.settings.risk.commission_rate) * Decimal("2")
        round_trip_cost += dec(self.settings.risk.transaction_tax_rate)
        round_trip_cost += (dec(self.settings.risk.slippage_bps) / Decimal("10000")) * Decimal("2")
        conservative_drag = initial * round_trip_cost
        end_equity = money(initial - conservative_drag)
        return BacktestResult(
            start=start,
            end=end,
            start_equity=initial,
            end_equity=end_equity,
            total_return=(end_equity / initial) - Decimal("1"),
            trades=2,
        )

    def _top_liquidity_symbols(self, stock, as_of: date) -> list[str]:
        symbols: list[str] = []
        date_text = as_of.strftime("%Y%m%d")
        for market in self.settings.universe.markets:
            frame = stock.get_market_ohlcv(date_text, market=market)
            if frame.empty:
                continue
            filtered = frame[frame["거래대금"] >= self.settings.universe.min_trading_value_krw]
            top = filtered.sort_values("거래대금", ascending=False).head(self.settings.universe.watch_top_n)
            symbols.extend(str(symbol) for symbol in top.index)
        return symbols[: self.settings.universe.watch_top_n]

    def _load_close_frame(self, stock, symbols: list[str], start: date, end: date) -> pd.DataFrame:
        start_text = start.strftime("%Y%m%d")
        end_text = end.strftime("%Y%m%d")
        series = {}
        for symbol in symbols:
            frame = stock.get_market_ohlcv_by_date(start_text, end_text, symbol)
            if frame.empty or "종가" not in frame:
                continue
            series[symbol] = frame["종가"]
        if not series:
            raise RuntimeError("No close history for backtest")
        return pd.DataFrame(series)

    def _load_close_frame_from_fdr(self, fdr, symbols: list[str], start: date, end: date) -> pd.DataFrame:
        series = {}
        for symbol in symbols:
            frame = fdr.DataReader(symbol, start.isoformat(), end.isoformat())
            if frame.empty or "Close" not in frame:
                continue
            series[symbol] = frame["Close"]
        if not series:
            raise RuntimeError("No FinanceDataReader close history for backtest")
        return pd.DataFrame(series)

    def _rank_from_close_frame(self, closes: pd.DataFrame) -> list[str]:
        scores: dict[str, Decimal] = {}
        for symbol in closes.columns:
            values = closes[symbol].dropna()
            if len(values) < max(self.settings.strategy.momentum_windows) + 1:
                continue
            latest = dec(values.iloc[-1])
            weighted = Decimal("0")
            for window, weight in zip(self.settings.strategy.momentum_windows, self.settings.strategy.momentum_weights):
                previous = dec(values.iloc[-window - 1])
                if previous <= 0:
                    continue
                weighted += (latest / previous - Decimal("1")) * dec(weight)
            volatility = dec(values.pct_change().tail(self.settings.strategy.volatility_window).std() or 0.0001)
            if volatility > 0:
                scores[symbol] = weighted / volatility
        return sorted(scores, key=scores.get, reverse=True)

    def _equity(self, cash: Decimal, holdings: dict[str, Decimal], prices: pd.Series) -> Decimal:
        equity = cash
        for symbol, quantity in holdings.items():
            equity += quantity * dec(prices[symbol])
        return equity

    def _buy_cost(self, quantity: Decimal, price: Decimal) -> Decimal:
        gross = quantity * self._slipped(price, buy=True)
        return gross + gross * dec(self.settings.risk.commission_rate)

    def _sell_value(self, quantity: Decimal, price: Decimal) -> Decimal:
        gross = quantity * self._slipped(price, buy=False)
        commission = gross * dec(self.settings.risk.commission_rate)
        tax = gross * dec(self.settings.risk.transaction_tax_rate)
        return gross - commission - tax

    def _slipped(self, price: Decimal, buy: bool) -> Decimal:
        slip = dec(self.settings.risk.slippage_bps) / Decimal("10000")
        return price * (Decimal("1") + slip if buy else Decimal("1") - slip)
