from __future__ import annotations

from datetime import date
from decimal import Decimal

from toss_bot.config import UniverseSettings
from toss_bot.models import MarketCountry, UniverseCandidate
from toss_bot.universe import UniverseBuilder


class RepoStub:
    def load_latest_universe(self, market=MarketCountry.KR):
        return []

    def save_universe(self, as_of, candidates, market=MarketCountry.KR):
        self.saved = (as_of, candidates, market)


class TossStub:
    def get_stocks(self, symbols):
        return [
            {
                "symbol": "000001",
                "status": "ACTIVE",
                "currency": "KRW",
                "securityType": "STOCK",
                "koreanMarketDetail": {"liquidationTrading": False, "krxTradingSuspended": False, "nxtTradingSuspended": False},
            },
            {
                "symbol": "000002",
                "status": "ACTIVE",
                "currency": "KRW",
                "securityType": "ETF",
                "koreanMarketDetail": {"liquidationTrading": False, "krxTradingSuspended": False, "nxtTradingSuspended": False},
            },
            {
                "symbol": "000003",
                "status": "ACTIVE",
                "currency": "KRW",
                "securityType": "STOCK",
                "koreanMarketDetail": {"liquidationTrading": False, "krxTradingSuspended": False, "nxtTradingSuspended": False},
            },
        ]

    def get_stock_warnings(self, symbol):
        if symbol == "000003":
            return [{"warningType": "OVERHEATED"}]
        return []


class UsTossStub:
    def get_stocks(self, symbols):
        return {
            "stocks": [
                {
                    "symbol": "AAPL",
                    "status": "ACTIVE",
                    "currency": "USD",
                    "securityType": "STOCK",
                    "isCommonShare": True,
                    "market": "NASDAQ",
                    "englishName": "Apple",
                },
                {
                    "symbol": "SPY",
                    "status": "ACTIVE",
                    "currency": "USD",
                    "securityType": "FOREIGN_ETF",
                    "market": "NYSE",
                    "englishName": "SPDR S&P 500 ETF",
                },
                {
                    "symbol": "PREF",
                    "status": "ACTIVE",
                    "currency": "USD",
                    "securityType": "FOREIGN_STOCK",
                    "isCommonShare": False,
                    "market": "NYSE",
                },
            ]
        }

    def get_candles(self, symbol, interval, count):
        return {
            "candles": [
                {
                    "timestamp": f"2026-06-{day:02d}T23:30:00+09:00",
                    "openPrice": "100.00",
                    "highPrice": "101.00",
                    "lowPrice": "99.00",
                    "closePrice": "100.00",
                    "volume": "1000000",
                }
                for day in range(1, 26)
            ]
        }


def test_verify_with_toss_filters_etf_and_warning_types():
    settings = UniverseSettings(excluded_warning_types=["OVERHEATED"])
    builder = UniverseBuilder(settings, RepoStub(), TossStub())
    candidates = [
        UniverseCandidate("000001", "a", "KOSPI", Decimal("10"), Decimal("1"), Decimal("1")),
        UniverseCandidate("000002", "b", "KOSPI", Decimal("9"), Decimal("1"), Decimal("1")),
        UniverseCandidate("000003", "c", "KOSDAQ", Decimal("8"), Decimal("1"), Decimal("1")),
    ]

    verified = builder._verify_kr_with_toss(candidates)

    assert [item.symbol for item in verified] == ["000001"]


def test_refresh_falls_back_to_cached_universe(monkeypatch):
    cached = [UniverseCandidate("000001", "a", "KOSPI", Decimal("10"), Decimal("1"), Decimal("1"))]

    class CachedRepo(RepoStub):
        def load_latest_universe(self, market=MarketCountry.KR):
            return cached

    builder = UniverseBuilder(UniverseSettings(), CachedRepo(), None)
    monkeypatch.setattr(builder, "_load_from_krx", lambda as_of: (_ for _ in ()).throw(RuntimeError("boom")))

    assert builder.refresh(date(2026, 6, 10)) == cached


def test_us_refresh_verifies_common_shares_and_saves_market():
    repository = RepoStub()
    settings = UniverseSettings(
        candidate_symbols=["AAPL", "SPY", "PREF"],
        min_trading_value=50_000_000,
        watch_top_n=10,
    )
    builder = UniverseBuilder(settings, repository, UsTossStub(), MarketCountry.US)

    candidates = builder.refresh(date(2026, 6, 10))

    assert [candidate.symbol for candidate in candidates] == ["AAPL"]
    assert repository.saved == (date(2026, 6, 10), candidates, MarketCountry.US)
