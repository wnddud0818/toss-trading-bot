from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal
from statistics import pstdev

from .config import CostSettings, StrategySettings
from .markets import align_price
from .models import Candle, MarketCountry, OrderSide, OrderType, Position, RankedCandidate, Signal, UniverseCandidate
from .utils import dec, qty

# 인접 분봉 간격이 이보다 크면 세션(거래일) 경계로 본다.
SESSION_GAP_MINUTES = 30
# 시장별 거래대금 만점 기준 (KR: 1000억 KRW, US: 1억 USD)
LIQUIDITY_FULL_SCORE_VALUE = {
    MarketCountry.KR: Decimal("100000000000"),
    MarketCountry.US: Decimal("100000000"),
}


class HybridMomentumStrategy:
    def __init__(
        self,
        settings: StrategySettings,
        costs: CostSettings | None = None,
        market: MarketCountry = MarketCountry.KR,
    ):
        self.settings = settings
        self.costs = costs or CostSettings.zero()
        self.market = market

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
        if len(daily_candles) < 2:
            return None
        # 비용 허들: 보유기간 동안 기대할 수 있는 변동(일변동성×√보유일)이
        # 왕복비용×배수를 넘지 못하면 수수료를 회수할 가능성이 낮으므로 진입하지 않는다.
        expected_move = candidate.volatility * dec(math.sqrt(self.settings.max_holding_days))
        if expected_move < self.round_trip_cost * dec(self.settings.min_edge_multiple):
            return None
        daily_sorted = sorted(daily_candles, key=lambda candle: candle.timestamp)
        # 장 초반에는 조회된 분봉 대부분이 전일 세션 데이터이므로 현재 세션 분봉만 사용한다.
        session = _session_slice(sorted(intraday_candles, key=lambda candle: candle.timestamp))
        if len(session) < self.settings.intraday_box_minutes + 2:
            return None
        latest = session[-1]
        # 루프가 분 초입에 돌므로 latest는 거래량이 수 초치뿐인 미완성 분봉이다.
        # 돌파·거래량 스파이크는 직전 완성 분봉으로 확인하고,
        # 미완성 분봉은 돌파 수준을 여전히 지키는지 확인하는 데만 쓴다.
        confirm = session[-2]
        session_open = session[0].open
        previous_day_high = daily_sorted[-2].high
        previous_close = daily_sorted[-2].close
        if session_open >= previous_close * (Decimal("1") + dec(self.settings.max_gap_up_pct)):
            return None
        if latest.close >= session_open * (Decimal("1") + dec(self.settings.max_intraday_extension_pct)):
            return None
        box = session[-self.settings.intraday_box_minutes - 2 : -2]
        box_high = max(candle.high for candle in box)
        breakout_level = max(previous_day_high, box_high) * (Decimal("1") + dec(self.settings.breakout_buffer_pct))
        avg_volume = sum(candle.volume for candle in box) / Decimal(len(box))
        volume_ok = confirm.volume >= avg_volume * dec(self.settings.volume_spike_multiplier)
        price_ok = confirm.close > breakout_level and latest.close > breakout_level
        if not (price_ok and volume_ok):
            return None
        if self.settings.require_vwap_confirmation and latest.close < self._vwap(session):
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
            limit_price=align_price(latest.close, side=OrderSide.BUY.value, market=self.market),
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
        session = _session_slice(sorted(intraday_candles, key=lambda candle: candle.timestamp))
        latest = session[-1]
        high_watermark = max(position.high_watermark, max(candle.high for candle in session))
        fixed_stop = position.entry_price * (Decimal("1") - dec(self.settings.stop_loss_pct))
        profit_from_entry = high_watermark / position.entry_price - Decimal("1")
        close_profit = latest.close / position.entry_price - Decimal("1")
        is_locked_winner = profit_from_entry >= dec(self.settings.profit_lock_trigger_pct)
        trailing_pct = dec(self.settings.trailing_stop_pct)
        trailing_reason = "trailing stop"
        if is_locked_winner:
            trailing_pct = dec(self.settings.profit_lock_trailing_stop_pct)
            trailing_reason = "profit lock trailing stop"
        elif not market_filter_ok:
            # 리스크오프에서 수익 포지션은 즉시 던지지 않고 트레일만 조여 추세 여력을 남긴다.
            trailing_pct = min(trailing_pct, dec(self.settings.profit_lock_trailing_stop_pct))
            trailing_reason = "risk-off tightened trailing stop"
        trailing_stop = high_watermark * (Decimal("1") - trailing_pct)
        breakeven_stop = None
        if profit_from_entry >= dec(self.settings.breakeven_trigger_pct):
            # 본전 보호는 왕복 비용까지 덮어야 실제로 본전이다.
            buffer = max(dec(self.settings.breakeven_buffer_pct), self.round_trip_cost)
            breakeven_stop = position.entry_price * (Decimal("1") + buffer)
        session_open = session[0].open
        daily_drop = latest.close <= session_open * (Decimal("1") - dec(self.settings.daily_drop_exit_pct))
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
        elif not market_filter_ok and close_profit < self.round_trip_cost:
            # 리스크오프 일괄 청산은 지수 MA 부근 왕복에서 비용만 태운다. 미수익 포지션만 정리한다.
            reason = "market filter risk-off"
        elif held_days >= self.settings.max_holding_days and not is_locked_winner:
            # 시간 청산은 추세를 못 만든 포지션용이다. 이익 보호 구간에 도달한
            # 승자는 조여진 트레일링이 관리하므로 강제 청산으로 추세를 자르지 않는다.
            reason = "max holding days"
        if reason is None:
            return None
        return Signal(
            symbol=position.symbol,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=position.quantity,
            limit_price=align_price(latest.close, side=OrderSide.SELL.value, market=self.market),
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
        # 최근 한 달 내 급등만 배제한다. 전체 이력으로 보면 강한 모멘텀 종목이
        # 과거 급등 이력 때문에 전부 걸러져 후보가 사라진다.
        recent = candles[-25:]
        max_5d = max(
            abs(recent[index].close / recent[index - 5].close - Decimal("1"))
            for index in range(5, len(recent))
            if recent[index - 5].close > 0
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
        return min(trading_value / LIQUIDITY_FULL_SCORE_VALUE[self.market], Decimal("1"))

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


def _session_slice(candles_sorted: list[Candle], max_gap_minutes: int = SESSION_GAP_MINUTES) -> list[Candle]:
    """최신 캔들부터 거슬러 올라가며 세션 경계(큰 시간 간격)에서 잘라 현재 세션 분봉만 남긴다.
    US 세션은 KST 자정을 넘기므로 날짜가 아니라 간격으로 자른다."""
    if not candles_sorted:
        return candles_sorted
    max_gap = timedelta(minutes=max_gap_minutes)
    start_index = 0
    for index in range(len(candles_sorted) - 1, 0, -1):
        if candles_sorted[index].timestamp - candles_sorted[index - 1].timestamp > max_gap:
            start_index = index
            break
    return candles_sorted[start_index:]
