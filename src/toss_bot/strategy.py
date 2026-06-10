from __future__ import annotations

import math
from datetime import date
from decimal import Decimal
from statistics import pstdev

from .config import CostSettings, StrategySettings
from .models import Candle, OrderSide, OrderType, Position, RankedCandidate, Signal, UniverseCandidate
from .utils import dec, money, qty


class HybridMomentumStrategy:
    def __init__(self, settings: StrategySettings, costs: CostSettings | None = None):
        self.settings = settings
        self.costs = costs or CostSettings.zero()

    @property
    def round_trip_cost(self) -> Decimal:
        """매수+매도 수수료, 매도 세금/수수료, 양방향 슬리피지를 합친 왕복 비용 비율."""
        return (
            dec(self.costs.commission_rate) * 2
            + dec(self.costs.sell_fee_rate)
            + dec(self.costs.slippage_bps) / Decimal("10000") * 2
        )

    def rank_candidates(
        self,
        universe: list[UniverseCandidate],
        daily_candles: dict[str, list[Candle]],
    ) -> list[RankedCandidate]:
        ranked: list[RankedCandidate] = []
        for candidate in universe:
            candles = sorted(daily_candles.get(candidate.symbol, []), key=lambda candle: candle.timestamp)
            min_window = max(self.settings.momentum_windows) + 1
            if len(candles) < min_window:
                continue
            if not self._passes_candidate_filters(candles):
                continue
            returns = self._window_returns(candles)
            volatility = self._volatility(candles[-self.settings.volatility_window :])
            if volatility <= 0:
                continue
            weighted = sum(
                returns[window] * dec(weight)
                for window, weight in zip(self.settings.momentum_windows, self.settings.momentum_weights)
            )
            score = weighted / volatility
            score += self._trend_quality(candles) * dec(self.settings.trend_quality_weight)
            score += self._volume_accumulation(candles) * dec(self.settings.volume_accumulation_weight)
            score += self._high_proximity(candles) * dec(self.settings.high_proximity_weight)
            score += self._liquidity_score(candidate.trading_value) * dec(self.settings.liquidity_weight)
            if score < dec(self.settings.min_score):
                continue
            ranked.append(
                RankedCandidate(
                    symbol=candidate.symbol,
                    name=candidate.name,
                    market=candidate.market,
                    score=score,
                    trading_value=candidate.trading_value,
                    volatility=volatility,
                )
            )
        return sorted(ranked, key=lambda item: (item.score, item.trading_value), reverse=True)

    def entry_signal(
        self,
        candidate: RankedCandidate,
        daily_candles: list[Candle],
        intraday_candles: list[Candle],
        budget: Decimal,
    ) -> Signal | None:
        if len(daily_candles) < 2 or len(intraday_candles) < self.settings.intraday_box_minutes + 1:
            return None
        # 비용 허들: 보유기간 동안 기대할 수 있는 변동(일변동성×√보유일)이
        # 왕복비용×배수를 넘지 못하면 수수료를 회수할 가능성이 낮으므로 진입하지 않는다.
        expected_move = candidate.volatility * dec(math.sqrt(self.settings.max_holding_days))
        if expected_move < self.round_trip_cost * dec(self.settings.min_edge_multiple):
            return None
        daily_sorted = sorted(daily_candles, key=lambda candle: candle.timestamp)
        intraday_sorted = sorted(intraday_candles, key=lambda candle: candle.timestamp)
        latest = intraday_sorted[-1]
        previous_day_high = daily_sorted[-2].high
        previous_close = daily_sorted[-2].close
        if latest.open >= previous_close * (Decimal("1") + dec(self.settings.max_gap_up_pct)):
            return None
        if latest.close >= intraday_sorted[0].open * (Decimal("1") + dec(self.settings.max_intraday_extension_pct)):
            return None
        box = intraday_sorted[-self.settings.intraday_box_minutes - 1 : -1]
        box_high = max(candle.high for candle in box)
        breakout_level = max(previous_day_high, box_high) * (Decimal("1") + dec(self.settings.breakout_buffer_pct))
        avg_volume = sum(candle.volume for candle in box) / Decimal(len(box))
        volume_ok = latest.volume >= avg_volume * dec(self.settings.volume_spike_multiplier)
        price_ok = latest.close > breakout_level
        if not (price_ok and volume_ok):
            return None
        if self.settings.require_vwap_confirmation and latest.close < self._vwap(intraday_sorted):
            return None
        if len(daily_sorted) >= 20:
            ma20 = self._moving_average(daily_sorted[-20:])
            if latest.close > ma20 * (Decimal("1") + dec(self.settings.max_distance_from_ma20_pct)):
                return None
        quantity = qty(budget / latest.close)
        if quantity <= 0:
            return None
        return Signal(
            symbol=candidate.symbol,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            limit_price=money(latest.close),
            reason="momentum breakout with volume spike",
        )

    def exit_signal(
        self,
        position: Position,
        intraday_candles: list[Candle],
        today: date,
        market_filter_ok: bool = True,
    ) -> Signal | None:
        if not intraday_candles:
            return None
        intraday_sorted = sorted(intraday_candles, key=lambda candle: candle.timestamp)
        latest = intraday_sorted[-1]
        high_watermark = max(position.high_watermark, latest.high)
        fixed_stop = position.entry_price * (Decimal("1") - dec(self.settings.stop_loss_pct))
        profit_from_entry = high_watermark / position.entry_price - Decimal("1")
        trailing_pct = dec(self.settings.trailing_stop_pct)
        trailing_reason = "trailing stop"
        if profit_from_entry >= dec(self.settings.profit_lock_trigger_pct):
            trailing_pct = dec(self.settings.profit_lock_trailing_stop_pct)
            trailing_reason = "profit lock trailing stop"
        trailing_stop = high_watermark * (Decimal("1") - trailing_pct)
        breakeven_stop = None
        if profit_from_entry >= dec(self.settings.breakeven_trigger_pct):
            # 본전 보호는 왕복 비용까지 덮어야 실제로 본전이다.
            buffer = max(dec(self.settings.breakeven_buffer_pct), self.round_trip_cost)
            breakeven_stop = position.entry_price * (Decimal("1") + buffer)
        open_price = intraday_sorted[0].open
        daily_drop = latest.close <= open_price * (Decimal("1") - dec(self.settings.daily_drop_exit_pct))
        held_days = (today - position.entry_date).days
        reason = None
        if latest.close <= fixed_stop:
            reason = "fixed stop loss"
        elif breakeven_stop is not None and latest.close <= breakeven_stop:
            reason = "breakeven profit protect"
        elif latest.close <= trailing_stop:
            reason = trailing_reason
        elif daily_drop:
            reason = "intraday drop exit"
        elif not market_filter_ok:
            reason = "market filter risk-off"
        elif held_days >= self.settings.max_holding_days:
            reason = "max holding days"
        if reason is None:
            return None
        return Signal(
            symbol=position.symbol,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=position.quantity,
            limit_price=money(latest.close),
            reason=reason,
        )

    def _window_returns(self, candles: list[Candle]) -> dict[int, Decimal]:
        latest = candles[-1].close
        values: dict[int, Decimal] = {}
        for window in self.settings.momentum_windows:
            previous = candles[-window - 1].close
            values[window] = latest / previous - Decimal("1")
        return values

    def _passes_candidate_filters(self, candles: list[Candle]) -> bool:
        if len(candles) < 61:
            return False
        latest = candles[-1].close
        return_20d = latest / candles[-21].close - Decimal("1")
        if return_20d < dec(self.settings.min_20d_return_pct):
            return False
        return_60d = latest / candles[-61].close - Decimal("1")
        if return_60d < dec(self.settings.min_60d_return_pct):
            return False
        recent_high = max(candle.high for candle in candles[-max(self.settings.momentum_windows) :])
        if recent_high > 0:
            drawdown = Decimal("1") - latest / recent_high
            if drawdown > dec(self.settings.max_drawdown_from_high_pct):
                return False
        if self._volume_accumulation_ratio(candles) < dec(self.settings.min_volume_accumulation_ratio):
            return False
        max_5d = max(
            abs(candles[index].close / candles[index - 5].close - Decimal("1"))
            for index in range(5, len(candles))
            if candles[index - 5].close > 0
        )
        if max_5d > dec(self.settings.max_5d_return_pct):
            return False
        if self.settings.require_trend_alignment:
            ma20 = self._moving_average(candles[-20:])
            ma60 = self._moving_average(candles[-60:])
            if not (latest > ma20 > ma60):
                return False
        return True

    def _moving_average(self, candles: list[Candle]) -> Decimal:
        return sum(candle.close for candle in candles) / Decimal(len(candles))

    def _trend_quality(self, candles: list[Candle]) -> Decimal:
        if len(candles) < 60:
            return Decimal("0")
        latest = candles[-1].close
        ma20 = self._moving_average(candles[-20:])
        ma60 = self._moving_average(candles[-60:])
        if ma20 <= 0 or ma60 <= 0:
            return Decimal("0")
        quality = (latest / ma20 - Decimal("1")) + (ma20 / ma60 - Decimal("1"))
        return min(max(quality, Decimal("0")), Decimal("1"))

    def _volume_accumulation_ratio(self, candles: list[Candle]) -> Decimal:
        if len(candles) < 60:
            return Decimal("0")
        avg20 = sum(candle.volume for candle in candles[-20:]) / Decimal("20")
        avg60 = sum(candle.volume for candle in candles[-60:]) / Decimal("60")
        if avg60 <= 0:
            return Decimal("0")
        return avg20 / avg60

    def _volume_accumulation(self, candles: list[Candle]) -> Decimal:
        ratio = self._volume_accumulation_ratio(candles)
        return min(max(ratio - Decimal("1"), Decimal("0")), Decimal("2"))

    def _high_proximity(self, candles: list[Candle]) -> Decimal:
        lookback = min(len(candles), max(self.settings.momentum_windows))
        recent_high = max(candle.high for candle in candles[-lookback:])
        if recent_high <= 0:
            return Decimal("0")
        drawdown = Decimal("1") - candles[-1].close / recent_high
        max_drawdown = dec(self.settings.max_drawdown_from_high_pct)
        if max_drawdown <= 0:
            return Decimal("0")
        return min(max(Decimal("1") - drawdown / max_drawdown, Decimal("0")), Decimal("1"))

    def _liquidity_score(self, trading_value: Decimal) -> Decimal:
        if trading_value <= 0:
            return Decimal("0")
        return min(trading_value / Decimal("100000000000"), Decimal("1"))

    def _vwap(self, candles: list[Candle]) -> Decimal:
        volume = sum(candle.volume for candle in candles)
        if volume <= 0:
            return candles[-1].close
        traded = sum(candle.close * candle.volume for candle in candles)
        return traded / volume

    def _volatility(self, candles: list[Candle]) -> Decimal:
        if len(candles) < 2:
            return Decimal("0")
        returns = [
            float(candles[index].close / candles[index - 1].close - Decimal("1"))
            for index in range(1, len(candles))
            if candles[index - 1].close > 0
        ]
        if not returns:
            return Decimal("0")
        return dec(max(pstdev(returns), 0.0001))
