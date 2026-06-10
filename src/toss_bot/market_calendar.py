from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .utils import KST


@dataclass(frozen=True)
class KrMarketSession:
    business_day: bool
    regular_start: datetime | None
    closing_auction_start: datetime | None
    regular_end: datetime | None

    def orders_open(self, now: datetime) -> bool:
        if not self.business_day or self.regular_start is None or self.regular_end is None:
            return False
        now = _aware_kst(now)
        return self.regular_start <= now < self.regular_end

    def new_entries_allowed(self, now: datetime) -> bool:
        if not self.orders_open(now):
            return False
        now = _aware_kst(now)
        cutoff = self.closing_auction_start or self.regular_end
        return cutoff is not None and now < cutoff

    def label(self) -> str:
        if not self.business_day or self.regular_start is None or self.regular_end is None:
            return "closed"
        close_cutoff = self.closing_auction_start or self.regular_end
        return (
            f"{self.regular_start.strftime('%H:%M')}-"
            f"{self.regular_end.strftime('%H:%M')} "
            f"entry_until={close_cutoff.strftime('%H:%M')}"
        )


def parse_kr_market_session(payload: dict) -> KrMarketSession:
    today = payload.get("today", payload)
    integrated = today.get("integrated") or {}
    regular = integrated.get("regularMarket") or {}
    regular_start = _parse_time(regular.get("startTime"))
    regular_end = _parse_time(regular.get("endTime"))
    auction_start = _parse_time(regular.get("singlePriceAuctionStartTime"))
    return KrMarketSession(
        business_day=regular_start is not None and regular_end is not None,
        regular_start=regular_start,
        closing_auction_start=auction_start,
        regular_end=regular_end,
    )


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return _aware_kst(datetime.fromisoformat(value))


def _aware_kst(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=KST)
    return value.astimezone(KST)
