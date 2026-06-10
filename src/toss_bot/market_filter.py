from __future__ import annotations

import logging
from datetime import date, timedelta

from .models import MarketCountry
from .utils import extract_items, parse_toss_candle, quiet_external_data_source

logger = logging.getLogger(__name__)

# 미국 시장 추세 판단용 대표 ETF (Toss 캔들로 조회)
US_INDEX_PROXIES = ("SPY", "QQQ")


class MarketFilter:
    def __init__(self, toss_client=None, lookback_days: int = 80, ma_window: int = 60):
        self.toss_client = toss_client
        self.lookback_days = lookback_days
        self.ma_window = ma_window

    def risk_on(self, market: MarketCountry, as_of: date) -> bool | None:
        try:
            if market == MarketCountry.KR:
                return self._kr_index_above_ma(as_of, "1001") and self._kr_index_above_ma(as_of, "2001")
            return all(self._us_proxy_above_ma(symbol) for symbol in US_INDEX_PROXIES)
        except Exception:
            logger.exception("Market filter failed for %s; blocking new entries without forcing risk-off exits", market)
            return None

    def _kr_index_above_ma(self, as_of: date, index_code: str) -> bool:
        from pykrx import stock

        start = (as_of - timedelta(days=self.lookback_days * 2)).strftime("%Y%m%d")
        end = as_of.strftime("%Y%m%d")
        with quiet_external_data_source():
            frame = stock.get_index_ohlcv_by_date(start, end, index_code)
        if frame.empty or len(frame) < self.ma_window:
            return False
        closes = frame["종가"].tail(self.ma_window)
        return float(closes.iloc[-1]) > float(closes.mean())

    def _us_proxy_above_ma(self, symbol: str) -> bool:
        if self.toss_client is None:
            raise RuntimeError("US market filter requires a Toss client")
        result = self.toss_client.get_candles(symbol, "1d", self.ma_window + 10)
        candles = [parse_toss_candle(item) for item in extract_items(result, "candles")]
        candles.sort(key=lambda candle: candle.timestamp)
        if len(candles) < self.ma_window:
            return False
        closes = [candle.close for candle in candles[-self.ma_window :]]
        return closes[-1] > sum(closes) / len(closes)
