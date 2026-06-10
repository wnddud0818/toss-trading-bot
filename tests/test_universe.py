from __future__ import annotations

from datetime import date
from decimal import Decimal

from toss_bot.config import UniverseSettings
from toss_bot.models import UniverseCandidate
from toss_bot.universe import UniverseBuilder


class RepoStub:
    def load_latest_universe(self):
        return []

    def save_universe(self, as_of, candidates):
        self.saved = (as_of, candidates)


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


def test_verify_with_toss_filters_etf_and_warning_types():
    settings = UniverseSettings(excluded_warning_types=["OVERHEATED"])
    builder = UniverseBuilder(settings, RepoStub(), TossStub())
    candidates = [
        UniverseCandidate("000001", "a", "KOSPI", Decimal("10"), Decimal("1"), Decimal("1")),
        UniverseCandidate("000002", "b", "KOSPI", Decimal("9"), Decimal("1"), Decimal("1")),
        UniverseCandidate("000003", "c", "KOSDAQ", Decimal("8"), Decimal("1"), Decimal("1")),
    ]

    verified = builder._verify_with_toss(candidates)

    assert [item.symbol for item in verified] == ["000001"]


def test_refresh_falls_back_to_cached_universe(monkeypatch):
    cached = [UniverseCandidate("000001", "a", "KOSPI", Decimal("10"), Decimal("1"), Decimal("1"))]

    class CachedRepo(RepoStub):
        def load_latest_universe(self):
            return cached

    builder = UniverseBuilder(UniverseSettings(), CachedRepo(), None)
    monkeypatch.setattr(builder, "_load_from_krx", lambda as_of: (_ for _ in ()).throw(RuntimeError("boom")))

    assert builder.refresh(date(2026, 6, 10)) == cached
