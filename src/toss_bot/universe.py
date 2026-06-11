from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Iterable

from .config import UniverseSettings
from .db import BotRepository
from .models import MarketCountry, UniverseCandidate
from .toss_client import TossClient
from .utils import dec, extract_items, parse_toss_candle, quiet_external_data_source

logger = logging.getLogger(__name__)


class UniverseBuilder:
    def __init__(
        self,
        settings: UniverseSettings,
        repository: BotRepository,
        toss_client: TossClient | None = None,
        market: MarketCountry = MarketCountry.KR,
    ):
        self.settings = settings
        self.repository = repository
        self.toss_client = toss_client
        self.market = market

    def refresh(self, as_of: date) -> list[UniverseCandidate]:
        try:
            if self.market == MarketCountry.KR:
                candidates = self._refresh_kr(as_of)
            else:
                candidates = self._refresh_us()
        except Exception:
            logger.exception("%s universe refresh failed; falling back to latest cached universe", self.market)
            cached = self.repository.load_latest_universe(self.market)
            if cached:
                return cached
            raise
        self.repository.save_universe(as_of, candidates, self.market)
        return candidates

    # --- KR -----------------------------------------------------------------

    def _refresh_kr(self, as_of: date) -> list[UniverseCandidate]:
        candidates = self._load_from_krx(as_of)
        candidates = self._filter_by_liquidity(candidates)
        return self._verify_kr_with_toss(candidates[: self.settings.watch_top_n])

    def _load_from_krx(self, as_of: date) -> list[UniverseCandidate]:
        try:
            return self._load_from_pykrx(as_of)
        except Exception as exc:
            logger.debug("pykrx universe source unavailable; trying FinanceDataReader: %s", exc)
            return self._load_from_finance_datareader()

    def _load_from_pykrx(self, as_of: date) -> list[UniverseCandidate]:
        date_text = as_of.strftime("%Y%m%d")
        rows: list[UniverseCandidate] = []
        with quiet_external_data_source():
            from pykrx import stock

            for market in self.settings.segments:
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
            if market not in self.settings.segments:
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
            if candidate.trading_value >= Decimal(str(self.settings.min_trading_value))
        ]
        return sorted(filtered, key=lambda item: item.trading_value, reverse=True)[: self.settings.liquidity_top_n]

    def _verify_kr_with_toss(self, candidates: list[UniverseCandidate]) -> list[UniverseCandidate]:
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

    # --- US -----------------------------------------------------------------

    def _refresh_us(self) -> list[UniverseCandidate]:
        if self.toss_client is None:
            raise RuntimeError("US universe requires a Toss client")
        pool = self._us_symbol_pool()
        if not pool:
            raise RuntimeError("US universe pool is empty")
        verified = self._verify_us_with_toss(pool)
        candidates: list[UniverseCandidate] = []
        for symbol, stock_info in verified.items():
            try:
                candidate = self._us_candidate_from_candles(symbol, stock_info)
            except Exception:
                logger.warning("Skipping US candidate %s: candle fetch failed", symbol, exc_info=True)
                continue
            if candidate is not None:
                candidates.append(candidate)
        if not candidates:
            raise RuntimeError("US universe verification returned no candidates")
        return sorted(candidates, key=lambda item: item.trading_value, reverse=True)[: self.settings.watch_top_n]

    def _us_symbol_pool(self) -> list[str]:
        symbols = list(self.settings.candidate_symbols)
        if self.settings.use_sp500_listing:
            try:
                import FinanceDataReader as fdr

                with quiet_external_data_source():
                    listing = fdr.StockListing("S&P500")
                column = "Symbol" if "Symbol" in listing.columns else "Code"
                symbols.extend(str(value) for value in listing[column].tolist())
            except Exception:
                logger.warning("S&P500 listing fetch failed; using configured candidate symbols", exc_info=True)
        seen: set[str] = set()
        unique: list[str] = []
        for symbol in symbols:
            normalized = symbol.strip().upper()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique.append(normalized)
        return unique[: self.settings.pool_cap]

    def _verify_us_with_toss(self, pool: list[str]) -> dict[str, dict]:
        allowed_types = {"FOREIGN_STOCK", "STOCK"}
        if self.settings.include_etf:
            allowed_types.update({"FOREIGN_ETF", "ETF"})
        verified: dict[str, dict] = {}
        for batch in _chunks(pool, 200):
            for stock_info in extract_items(self.toss_client.get_stocks(batch), "stocks", "items"):
                symbol = stock_info.get("symbol")
                security_type = stock_info.get("securityType")
                if symbol not in pool or stock_info.get("status") != "ACTIVE":
                    continue
                if stock_info.get("currency") != "USD":
                    continue
                if security_type not in allowed_types:
                    continue
                if security_type in {"FOREIGN_STOCK", "STOCK"} and not stock_info.get("isCommonShare", True):
                    continue
                verified[symbol] = stock_info
        return verified

    def _us_candidate_from_candles(self, symbol: str, stock_info: dict) -> UniverseCandidate | None:
        result = self.toss_client.get_candles(symbol, "1d", 25)
        candles = [parse_toss_candle(item) for item in extract_items(result, "candles")]
        candles.sort(key=lambda candle: candle.timestamp)
        if len(candles) < 20:
            return None
        recent = candles[-20:]
        dollar_volume = sum(candle.close * candle.volume for candle in recent) / Decimal(len(recent))
        if dollar_volume < Decimal(str(self.settings.min_trading_value)):
            return None
        latest = candles[-1]
        return UniverseCandidate(
            symbol=symbol,
            name=stock_info.get("englishName") or stock_info.get("name") or symbol,
            market=stock_info.get("market", "US_ETC"),
            trading_value=dollar_volume,
            close=latest.close,
            volume=latest.volume,
        )


def _chunks(values: list[str], size: int):
    for index in range(0, len(values), size):
        yield values[index : index + size]
