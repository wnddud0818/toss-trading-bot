from __future__ import annotations

from datetime import date

from toss_bot.market_filter import KR_FDR_INDEX_CODES, MarketFilter
from toss_bot.models import MarketCountry


def test_kr_market_filter_falls_back_to_fdr_when_pykrx_fails(monkeypatch):
    market_filter = MarketFilter(ma_window=60)
    fallback_calls = []

    def unavailable_pykrx(as_of, code):
        raise RuntimeError("krx unavailable")

    def available_fdr(as_of, code):
        fallback_calls.append(code)
        return True

    monkeypatch.setattr(market_filter, "_kr_pykrx_index_above_ma", unavailable_pykrx)
    monkeypatch.setattr(market_filter, "_kr_fdr_index_above_ma", available_fdr)

    assert market_filter.risk_on(MarketCountry.KR, date(2026, 6, 11)) is True
    assert fallback_calls == list(KR_FDR_INDEX_CODES)
