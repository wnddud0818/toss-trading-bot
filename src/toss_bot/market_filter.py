from __future__ import annotations

import logging
import time
from datetime import date, timedelta

from .models import MarketCountry
from .utils import extract_items, parse_toss_candle, quiet_external_data_source

logger = logging.getLogger(__name__)

# KR market trend checks use direct index data. pykrx is preferred and FDR is
# used as a no-login fallback when KRX blocks or changes the response format.
KR_PYKRX_INDEX_CODES = ("1001", "2001")
KR_FDR_INDEX_CODES = ("KS11", "KQ11")
# US market trend proxies queried through Toss candles.
US_INDEX_PROXIES = ("SPY", "QQQ")


class MarketFilter:
    def __init__(
        self,
        toss_client=None,
        lookback_days: int = 80,
        ma_window: int = 60,
        failure_log_cooldown_seconds: int = 1800,
    ):
        self.toss_client = toss_client
        self.lookback_days = lookback_days
        self.ma_window = ma_window
        self.failure_log_cooldown_seconds = failure_log_cooldown_seconds
        self._last_failure_log: dict[MarketCountry, float] = {}
        self._kr_pykrx_available = True

    def risk_on(self, market: MarketCountry, as_of: date) -> bool | None:
        try:
            if market == MarketCountry.KR:
                return self._kr_risk_on(as_of)
            return all(self._toss_proxy_above_ma(symbol) for symbol in US_INDEX_PROXIES)
        except Exception as exc:
            self._log_failure(market, exc)
            return None

    def _log_failure(self, market: MarketCountry, exc: Exception) -> None:
        now = time.monotonic()
        last = self._last_failure_log.get(market)
        if last is not None and now - last < self.failure_log_cooldown_seconds:
            logger.debug("Market filter still unavailable for %s; blocking new entries: %s", market, exc)
            return
        self._last_failure_log[market] = now
        logger.warning(
            "Market filter failed for %s; blocking new entries without forcing risk-off exits: %s",
            market,
            exc,
            exc_info=True,
        )

    def _kr_risk_on(self, as_of: date) -> bool:
        if self._kr_pykrx_available:
            try:
                return all(self._kr_pykrx_index_above_ma(as_of, code) for code in KR_PYKRX_INDEX_CODES)
            except Exception as exc:
                self._kr_pykrx_available = False
                logger.debug("pykrx KR market filter unavailable; falling back to FinanceDataReader: %s", exc)
        return all(self._kr_fdr_index_above_ma(as_of, code) for code in KR_FDR_INDEX_CODES)

    def _kr_pykrx_index_above_ma(self, as_of: date, index_code: str) -> bool:
        start = (as_of - timedelta(days=self.lookback_days * 2)).strftime("%Y%m%d")
        end = as_of.strftime("%Y%m%d")
        with quiet_external_data_source():
            from pykrx import stock

            frame = stock.get_index_ohlcv_by_date(start, end, index_code)
        if frame.empty or len(frame) < self.ma_window:
            return False
        closes = frame["종가"].tail(self.ma_window)
        return float(closes.iloc[-1]) > float(closes.mean())

    def _kr_fdr_index_above_ma(self, as_of: date, index_code: str) -> bool:
        import FinanceDataReader as fdr

        start = (as_of - timedelta(days=self.lookback_days * 2)).isoformat()
        end = as_of.isoformat()
        with quiet_external_data_source():
            frame = fdr.DataReader(index_code, start, end)
        if frame.empty or len(frame) < self.ma_window or "Close" not in frame:
            return False
        closes = frame["Close"].tail(self.ma_window)
        return float(closes.iloc[-1]) > float(closes.mean())

    def _toss_proxy_above_ma(self, symbol: str) -> bool:
        if self.toss_client is None:
            raise RuntimeError("market filter requires a Toss client")
        result = self.toss_client.get_candles(symbol, "1d", self.ma_window + 10)
        candles = [parse_toss_candle(item) for item in extract_items(result, "candles")]
        candles.sort(key=lambda candle: candle.timestamp)
        if len(candles) < self.ma_window:
            return False
        closes = [candle.close for candle in candles[-self.ma_window :]]
        return closes[-1] > sum(closes) / len(closes)
