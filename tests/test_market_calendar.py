from __future__ import annotations

from datetime import datetime

from toss_bot.market_calendar import parse_kr_market_session
from toss_bot.utils import KST


def test_kr_market_session_blocks_entries_after_closing_auction_start():
    session = parse_kr_market_session(
        {
            "today": {
                "integrated": {
                    "regularMarket": {
                        "startTime": "2026-03-25T09:00:00+09:00",
                        "singlePriceAuctionStartTime": "2026-03-25T15:20:00+09:00",
                        "endTime": "2026-03-25T15:30:00+09:00",
                    }
                }
            }
        }
    )

    assert session.orders_open(datetime(2026, 3, 25, 15, 25, tzinfo=KST))
    assert not session.new_entries_allowed(datetime(2026, 3, 25, 15, 25, tzinfo=KST))


def test_kr_market_session_handles_holiday_payload():
    session = parse_kr_market_session({"today": {"date": "2026-03-01", "integrated": None}})

    assert not session.orders_open(datetime(2026, 3, 1, 10, 0, tzinfo=KST))
