from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .models import MarketCountry
from .utils import KST


@dataclass(frozen=True)
class MarketSession:
    business_day: bool
    regular_start: datetime | None
    regular_end: datetime | None
    entry_cutoff: datetime | None

    def orders_open(self, now: datetime) -> bool:
        if not self.business_day or self.regular_start is None or self.regular_end is None:
            return False
        now = _aware_kst(now)
        return self.regular_start <= now < self.regular_end

    def new_entries_allowed(self, now: datetime) -> bool:
        if not self.orders_open(now):
            return False
        now = _aware_kst(now)
        cutoff = self.entry_cutoff or self.regular_end
        return cutoff is not None and now < cutoff

    def label(self) -> str:
        if not self.business_day or self.regular_start is None or self.regular_end is None:
            return "closed"
        cutoff = self.entry_cutoff or self.regular_end
        return (
            f"{self.regular_start.strftime('%H:%M')}-"
            f"{self.regular_end.strftime('%H:%M')} "
            f"entry_until={cutoff.strftime('%H:%M')}"
        )


def parse_market_session(
    payload: dict,
    market: MarketCountry = MarketCountry.KR,
    entry_cutoff_minutes: int = 0,
) -> MarketSession:
    """KR은 today.integrated.regularMarket(+종가 단일가), US는 today.regularMarket을 읽는다.
    응답의 모든 시각은 KST 기준이므로 US 세션은 KST 자정을 넘는 구간이 될 수 있다."""
    today = payload.get("today", payload)
    if market == MarketCountry.KR:
        regular = (today.get("integrated") or {}).get("regularMarket") or {}
        auction_start = _parse_time(regular.get("singlePriceAuctionStartTime"))
    else:
        regular = today.get("regularMarket") or {}
        auction_start = None
    regular_start = _parse_time(regular.get("startTime"))
    regular_end = _parse_time(regular.get("endTime"))
    cutoff = auction_start
    if cutoff is None and regular_end is not None and entry_cutoff_minutes > 0:
        cutoff = regular_end - timedelta(minutes=entry_cutoff_minutes)
    return MarketSession(
        business_day=regular_start is not None and regular_end is not None,
        regular_start=regular_start,
        regular_end=regular_end,
        entry_cutoff=cutoff or regular_end,
    )


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return _aware_kst(datetime.fromisoformat(value))


def _aware_kst(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=KST)
    return value.astimezone(KST)
