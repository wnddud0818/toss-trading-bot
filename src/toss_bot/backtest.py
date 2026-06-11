from __future__ import annotations

import math
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


@dataclass
class _SimPosition:
    quantity: Decimal
    entry_price: Decimal
    entry_date: date
    high_watermark: Decimal


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
                    frames = loader(start, end)
                return self._rotation_backtest(
                    frames, start, end, profile.strategy, profile.costs, initial, currency
                )
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        return self._fallback_cost_smoke(start, end, profile.costs, initial, currency, "; ".join(errors))

    # --- 데이터 로더 ---------------------------------------------------------

    def _load_kr_closes_krx(self, start: date, end: date) -> dict[str, pd.DataFrame]:
        from pykrx import stock

        profile = self.settings.market_profile(MarketCountry.KR)
        lookback_start = start - timedelta(days=260)
        symbols: list[str] = []
        # 기준일이 휴장일이거나 KRX 응답이 비면 pykrx가 깨지므로 영업일을 거슬러 폴백한다.
        for offset in range(8):
            date_text = (end - timedelta(days=offset)).strftime("%Y%m%d")
            try:
                for segment in profile.universe.segments:
                    frame = stock.get_market_ohlcv(date_text, market=segment)
                    if frame.empty or "거래대금" not in frame:
                        continue
                    filtered = frame[frame["거래대금"] >= profile.universe.min_trading_value]
                    top = filtered.sort_values("거래대금", ascending=False).head(profile.universe.watch_top_n)
                    symbols.extend(str(symbol) for symbol in top.index)
            except Exception:
                symbols = []
                continue
            if symbols:
                break
        symbols = symbols[: profile.universe.watch_top_n]
        if not symbols:
            raise RuntimeError("No KRX symbols for backtest")
        columns = {"open": "시가", "high": "고가", "low": "저가", "close": "종가"}
        series: dict[str, dict[str, pd.Series]] = {key: {} for key in columns}
        for symbol in symbols:
            frame = stock.get_market_ohlcv_by_date(
                lookback_start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), symbol
            )
            if frame.empty or "종가" not in frame:
                continue
            for key, column in columns.items():
                if column in frame:
                    series[key][symbol] = frame[column]
        if not series["close"]:
            raise RuntimeError("No close history for backtest")
        return {key: pd.DataFrame(values) for key, values in series.items() if values}

    def _load_kr_closes_fdr(self, start: date, end: date) -> dict[str, pd.DataFrame]:
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

    def _load_us_closes_fdr(self, start: date, end: date) -> dict[str, pd.DataFrame]:
        import FinanceDataReader as fdr

        profile = self.settings.market_profile(MarketCountry.US)
        symbols = [
            symbol.replace(".", "-")  # FDR(야후 계열)은 BRK.B 대신 BRK-B 표기를 쓴다
            for symbol in profile.universe.candidate_symbols[: profile.universe.watch_top_n * 2]
        ]
        if not symbols:
            raise RuntimeError("No US candidate symbols configured for backtest")
        return self._load_fdr_frame(fdr, symbols, start - timedelta(days=260), end)

    def _load_fdr_frame(self, fdr, symbols: list[str], start: date, end: date) -> dict[str, pd.DataFrame]:
        columns = {"open": "Open", "high": "High", "low": "Low", "close": "Close"}
        series: dict[str, dict[str, pd.Series]] = {key: {} for key in columns}
        for symbol in symbols:
            try:
                frame = fdr.DataReader(symbol, start.isoformat(), end.isoformat())
            except Exception:
                continue
            if frame.empty or "Close" not in frame:
                continue
            for key, column in columns.items():
                if column in frame:
                    series[key][symbol] = frame[column]
        if not series["close"]:
            raise RuntimeError("No FinanceDataReader close history for backtest")
        return {key: pd.DataFrame(values) for key, values in series.items() if values}

    # --- 시뮬레이션 ----------------------------------------------------------

    def _rotation_backtest(
        self,
        frames: dict[str, pd.DataFrame],
        start: date,
        end: date,
        strategy_settings: StrategySettings,
        costs: CostSettings,
        initial: Decimal,
        currency: str,
    ) -> BacktestResult:
        closes = frames["close"].dropna(axis=1, thresh=140).ffill()
        opens = self._aligned(frames.get("open"), closes)
        highs = self._aligned(frames.get("high"), closes)
        lows = self._aligned(frames.get("low"), closes)
        trading_days = [day.date() for day in closes.index if start <= day.date() <= end]
        if not trading_days:
            raise RuntimeError("No trading days for backtest")

        strategy = HybridMomentumStrategy(strategy_settings, costs)
        round_trip = strategy.round_trip_cost
        # 변동성 적응 스탑과 비용 허들에 쓰는 20일 일변동성, 동일가중 레짐 지수(MA60)
        volatility_frame = closes.pct_change().rolling(strategy_settings.volatility_window).std()
        index_series = closes.mean(axis=1)
        index_ma = index_series.rolling(60).mean()
        edge_hurdle = round_trip * dec(strategy_settings.min_edge_multiple)
        sqrt_holding = dec(math.sqrt(strategy_settings.max_holding_days))
        cash = initial
        holdings: dict[str, _SimPosition] = {}
        last_sell: dict[str, date] = {}
        trades = 0
        max_window = max(strategy_settings.momentum_windows)
        last_rebalance_week: tuple[int, int] | None = None

        def symbol_volatility(timestamp: pd.Timestamp, symbol: str) -> Decimal | None:
            value = volatility_frame.at[timestamp, symbol]
            return None if pd.isna(value) else dec(value)

        for day in trading_days:
            timestamp = pd.Timestamp(day)
            row_close = closes.loc[timestamp]
            row_open = opens.loc[timestamp] if opens is not None else row_close
            row_high = highs.loc[timestamp] if highs is not None else row_close
            row_low = lows.loc[timestamp] if lows is not None else row_close
            index_value = index_series.loc[timestamp]
            index_mean = index_ma.loc[timestamp]
            risk_on = pd.isna(index_mean) or index_value >= index_mean

            # 실전 청산 엔진을 일봉 OHLC로 근사: 손절/트레일링/본전보호/리스크오프/시간청산
            for symbol, position in list(holdings.items()):
                if pd.isna(row_close[symbol]):
                    continue
                close_price = dec(row_close[symbol])
                open_price = dec(row_open[symbol]) if not pd.isna(row_open[symbol]) else close_price
                high_price = dec(row_high[symbol]) if not pd.isna(row_high[symbol]) else close_price
                low_price = dec(row_low[symbol]) if not pd.isna(row_low[symbol]) else close_price
                # 당일 고가를 먼저 반영하면 "고가 후 저가" 최악 경로를 가정하게 되어
                # 일중 변동이 트레일 폭을 넘는 날마다 무조건 청산된다.
                # 표준 관행대로 스탑 판정은 전일까지의 고점 기준, 당일 고가는 판정 후 반영한다.
                prior_high_watermark = position.high_watermark
                profit_hwm = prior_high_watermark / position.entry_price - Decimal("1")
                is_locked_winner = profit_hwm >= dec(strategy_settings.profit_lock_trigger_pct)
                volatility = symbol_volatility(timestamp, symbol)
                if is_locked_winner:
                    trail_pct = dec(strategy_settings.profit_lock_trailing_stop_pct)
                else:
                    trail_pct = strategy.effective_trailing_stop_pct(volatility)
                    if not risk_on:
                        trail_pct = min(trail_pct, dec(strategy_settings.profit_lock_trailing_stop_pct))
                stop = position.entry_price * (Decimal("1") - strategy.effective_stop_loss_pct(volatility))
                stop = max(stop, prior_high_watermark * (Decimal("1") - trail_pct))
                if profit_hwm >= dec(strategy_settings.breakeven_trigger_pct):
                    buffer = max(dec(strategy_settings.breakeven_buffer_pct), round_trip)
                    stop = max(stop, position.entry_price * (Decimal("1") + buffer))
                exit_price = None
                if open_price > 0 and open_price <= stop:
                    exit_price = open_price  # 갭하락은 스탑가가 아니라 시가 체결로 근사
                elif low_price <= stop:
                    exit_price = stop
                elif not risk_on and close_price < position.entry_price * (Decimal("1") + round_trip):
                    exit_price = close_price  # 리스크오프: 미수익 포지션만 정리
                elif (
                    (day - position.entry_date).days >= strategy_settings.max_holding_days
                    and not is_locked_winner
                ):
                    exit_price = close_price
                if exit_price is not None:
                    cash += self._sell_value(position.quantity, exit_price, costs)
                    del holdings[symbol]
                    last_sell[symbol] = day
                    trades += 1
                else:
                    position.high_watermark = max(prior_high_watermark, high_price)

            # 룩백 데이터는 시작일 이전 260일치를 이미 로드했으므로 워밍업 스킵 없이
            # 첫 거래일과 매주 첫 거래일(월요일 휴장 포함)에 신규 진입을 평가한다.
            iso = day.isocalendar()
            week = (iso[0], iso[1])
            if week == last_rebalance_week:
                continue
            last_rebalance_week = week
            if not risk_on:
                continue  # 레짐 필터: 지수가 MA60 아래면 신규 진입 금지 (실전 MarketFilter와 동일 방향)
            prices = closes.loc[:timestamp].tail(max_window + 1)
            ranked = self._rank_from_close_frame(prices, strategy_settings)
            if not ranked:
                continue
            quantities = {symbol: position.quantity for symbol, position in holdings.items()}
            equity = self._equity(cash, quantities, row_close)
            base_weight = min(
                dec(self.settings.risk.max_symbol_weight),
                (Decimal("1") - dec(self.settings.risk.min_cash_weight)) / Decimal(strategy_settings.max_positions),
            )
            reserve = equity * dec(self.settings.risk.min_cash_weight)
            for symbol in ranked:
                if len(holdings) >= strategy_settings.max_positions:
                    break
                if symbol in holdings or pd.isna(row_close[symbol]):
                    continue
                sold_on = last_sell.get(symbol)
                if sold_on is not None and (day - sold_on).days < strategy_settings.reentry_cooldown_days:
                    continue
                price = dec(row_close[symbol])
                if price <= 0:
                    continue
                volatility = symbol_volatility(timestamp, symbol)
                # 실전과 동일한 비용 허들: 기대변동이 왕복비용×배수에 못 미치면 진입하지 않는다
                if volatility is None or volatility * sqrt_holding < edge_hurdle:
                    continue
                # 스탑이 넓어진 만큼 비중을 줄여 1회 손실을 max_entry_risk_pct로 고정한다
                effective_stop = strategy.effective_stop_loss_pct(volatility)
                weight = min(base_weight, dec(self.settings.risk.max_entry_risk_pct) / effective_stop)
                target_value = equity * weight
                quantity = (target_value / price).to_integral_value(rounding=ROUND_DOWN)
                total_cost = self._buy_cost(quantity, price, costs)
                if quantity > 0 and total_cost <= cash - reserve:
                    cash -= total_cost
                    fill_price = self._slipped(price, costs, buy=True)
                    holdings[symbol] = _SimPosition(quantity, fill_price, day, fill_price)
                    trades += 1

        final_prices = closes.loc[pd.Timestamp(trading_days[-1])]
        final_quantities = {symbol: position.quantity for symbol, position in holdings.items()}
        end_equity = money(self._equity(cash, final_quantities, final_prices))
        return BacktestResult(
            start=start,
            end=end,
            start_equity=initial,
            end_equity=end_equity,
            total_return=(end_equity / initial) - Decimal("1"),
            trades=trades,
            method="daily_ohlc_sim_with_stops",
            currency=currency,
            warning=(
                "Proxy backtest: entries are weekly at close (no intraday breakout/orderbook); "
                "stops/time exits approximated on daily OHLC; regime filter uses equal-weight "
                "universe index vs MA60."
            ),
        )

    def _aligned(self, frame: pd.DataFrame | None, closes: pd.DataFrame) -> pd.DataFrame | None:
        if frame is None:
            return None
        return frame.reindex(index=closes.index, columns=closes.columns).ffill()

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
