from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Iterable

from .config import UniverseSettings
from .db import BotRepository
from .models import UniverseCandidate
from .toss_client import TossClient
from .utils import dec, extract_items, quiet_external_data_source

logger = logging.getLogger(__name__)


class UniverseBuilder:
    def __init__(
        self,
        settings: UniverseSettings,
        repository: BotRepository,
        toss_client: TossClient | None = None,
    ):
        self.settings = settings
        self.repository = repository
        self.toss_client = toss_client

    def refresh(self, as_of: date) -> list[UniverseCandidate]:
        try:
            candidates = self._load_from_krx(as_of)
        except Exception:
            logger.exception("KRX universe refresh failed; falling back to latest cached universe")
            cached = self.repository.load_latest_universe()
            if cached:
                return cached
            raise
        candidates = self._filter_by_liquidity(candidates)
        candidates = self._verify_with_toss(candidates[: self.settings.watch_top_n])
        self.repository.save_universe(as_of, candidates)
        return candidates

    def _load_from_krx(self, as_of: date) -> list[UniverseCandidate]:
        try:
            return self._load_from_pykrx(as_of)
        except Exception:
            logger.exception("pykrx universe source failed; trying FinanceDataReader")
            return self._load_from_finance_datareader()

    def _load_from_pykrx(self, as_of: date) -> list[UniverseCandidate]:
        from pykrx import stock

        date_text = as_of.strftime("%Y%m%d")
        rows: list[UniverseCandidate] = []
        with quiet_external_data_source():
            for market in self.settings.markets:
                tickers = stock.get_market_ticker_list(date_text, market=market)
                ohlcv = stock.get_market_ohlcv(date_text, market=market)
                if ohlcv.empty:
                    continue
                for symbol in tickers:
                    if symbol not in ohlcv.index:
                        continue
                    row = ohlcv.loc[symbol]
                    trading_value = dec(row.get("거래대금", 0))
                    close = dec(row.get("종가", 0))
                    volume = dec(row.get("거래량", 0))
                    if trading_value <= 0 or close <= 0:
                        continue
                    rows.append(
                        UniverseCandidate(
                            symbol=symbol,
                            name=stock.get_market_ticker_name(symbol),
                            market=market,
                            trading_value=trading_value,
                            close=close,
                            volume=volume,
                        )
                    )
        if not rows:
            raise RuntimeError("KRX returned no candidates")
        return rows

    def _load_from_finance_datareader(self) -> list[UniverseCandidate]:
        import pandas as pd
        import FinanceDataReader as fdr

        with quiet_external_data_source():
            listing = fdr.StockListing("KRX")
        if listing.empty:
            raise RuntimeError("FinanceDataReader returned no KRX listing")
        market_column = "Market" if "Market" in listing.columns else "MarketId"
        rows: list[UniverseCandidate] = []
        for _, row in listing.iterrows():
            market = str(row.get(market_column, ""))
            if market not in self.settings.markets:
                continue
            symbol = str(row.get("Code", "")).zfill(6)
            close_value = row.get("Close", 0)
            volume_value = row.get("Volume", 0)
            close = dec(0 if pd.isna(close_value) else close_value)
            volume = dec(0 if pd.isna(volume_value) else volume_value)
            amount_value = row.get("Amount", None)
            trading_value = dec(amount_value if amount_value is not None and not pd.isna(amount_value) else close * volume)
            if not symbol or trading_value <= 0 or close <= 0:
                continue
            rows.append(
                UniverseCandidate(
                    symbol=symbol,
                    name=str(row.get("Name", symbol)),
                    market=market,
                    trading_value=trading_value,
                    close=close,
                    volume=volume,
                )
            )
        if not rows:
            raise RuntimeError("FinanceDataReader returned no usable KRX candidates")
        return rows

    def _filter_by_liquidity(self, candidates: Iterable[UniverseCandidate]) -> list[UniverseCandidate]:
        filtered = [
            candidate
            for candidate in candidates
            if candidate.trading_value >= Decimal(self.settings.min_trading_value_krw)
        ]
        return sorted(filtered, key=lambda item: item.trading_value, reverse=True)[: self.settings.liquidity_top_n]

    def _verify_with_toss(self, candidates: list[UniverseCandidate]) -> list[UniverseCandidate]:
        if self.toss_client is None:
            return candidates
        allowed = {candidate.symbol: candidate for candidate in candidates}
        verified_symbols: set[str] = set()
        for batch in _chunks(list(allowed), 200):
            for stock_info in extract_items(self.toss_client.get_stocks(batch), "stocks", "items"):
                symbol = stock_info.get("symbol")
                if symbol not in allowed or stock_info.get("status") != "ACTIVE":
                    continue
                if stock_info.get("currency") != "KRW":
                    continue
                if not self.settings.include_etf and stock_info.get("securityType") != "STOCK":
                    continue
                detail = stock_info.get("koreanMarketDetail") or {}
                if detail.get("liquidationTrading"):
                    continue
                if detail.get("krxTradingSuspended") or detail.get("nxtTradingSuspended"):
                    continue
                verified_symbols.add(symbol)

        safe: list[UniverseCandidate] = []
        excluded_warning_types = set(self.settings.excluded_warning_types)
        for symbol in verified_symbols:
            warnings = extract_items(self.toss_client.get_stock_warnings(symbol), "warnings", "items")
            warning_types = {warning.get("warningType") for warning in warnings}
            if warning_types & excluded_warning_types:
                continue
            safe.append(allowed[symbol])
        return sorted(safe, key=lambda item: item.trading_value, reverse=True)


def _chunks(values: list[str], size: int):
    for index in range(0, len(values), size):
        yield values[index : index + size]
