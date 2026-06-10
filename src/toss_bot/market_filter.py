from __future__ import annotations

import logging
from datetime import date, timedelta

from .utils import quiet_external_data_source

logger = logging.getLogger(__name__)


class MarketFilter:
    def __init__(self, lookback_days: int = 80, ma_window: int = 60):
        self.lookback_days = lookback_days
        self.ma_window = ma_window

    def risk_on(self, as_of: date) -> bool:
        try:
            return self._index_above_ma(as_of, "1001") and self._index_above_ma(as_of, "2001")
        except Exception:
            logger.exception("Market filter failed; blocking new entries")
            return False

    def _index_above_ma(self, as_of: date, index_code: str) -> bool:
        from pykrx import stock

        start = (as_of - timedelta(days=self.lookback_days * 2)).strftime("%Y%m%d")
        end = as_of.strftime("%Y%m%d")
        with quiet_external_data_source():
            frame = stock.get_index_ohlcv_by_date(start, end, index_code)
        if frame.empty or len(frame) < self.ma_window:
            return False
        closes = frame["종가"].tail(self.ma_window)
        return float(closes.iloc[-1]) > float(closes.mean())
