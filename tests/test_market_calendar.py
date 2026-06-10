from __future__ import annotations

from datetime import datetime

from toss_bot.market_calendar import parse_market_session
from toss_bot.models import MarketCountry
from toss_bot.utils import KST


def test_kr_market_session_blocks_entries_after_closing_auction_start():
    session = parse_market_session(
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
        },
        MarketCountry.KR,
    )

    assert session.orders_open(datetime(2026, 3, 25, 15, 25, tzinfo=KST))
    assert not session.new_entries_allowed(datetime(2026, 3, 25, 15, 25, tzinfo=KST))


def test_kr_market_session_handles_holiday_payload():
    session = parse_market_session({"today": {"date": "2026-03-01", "integrated": None}}, MarketCountry.KR)

    assert not session.orders_open(datetime(2026, 3, 1, 10, 0, tzinfo=KST))


def test_us_market_session_spans_kst_midnight():
    session = parse_market_session(
        {
            "today": {
                "date": "2026-03-24",
                "regularMarket": {
                    "startTime": "2026-03-24T22:30:00+09:00",
                    "endTime": "2026-03-25T05:00:00+09:00",
                },
            }
        },
        MarketCountry.US,
        entry_cutoff_minutes=30,
    )

    assert session.orders_open(datetime(2026, 3, 24, 23, 0, tzinfo=KST))
    assert session.orders_open(datetime(2026, 3, 25, 3, 0, tzinfo=KST))
    assert not session.orders_open(datetime(2026, 3, 25, 5, 30, tzinfo=KST))
    assert session.new_entries_allowed(datetime(2026, 3, 25, 4, 0, tzinfo=KST))
    assert not session.new_entries_allowed(datetime(2026, 3, 25, 4, 45, tzinfo=KST))


def test_us_market_session_selects_previous_business_day_after_kst_midnight():
    session = parse_market_session(
        {
            "previousBusinessDay": {
                "date": "2026-03-24",
                "regularMarket": {
                    "startTime": "2026-03-24T22:30:00+09:00",
                    "endTime": "2026-03-25T05:00:00+09:00",
                },
            },
            "today": {
                "date": "2026-03-25",
                "regularMarket": {
                    "startTime": "2026-03-25T22:30:00+09:00",
                    "endTime": "2026-03-26T05:00:00+09:00",
                },
            },
        },
        MarketCountry.US,
        entry_cutoff_minutes=30,
        now=datetime(2026, 3, 25, 3, 0, tzinfo=KST),
    )

    assert session.orders_open(datetime(2026, 3, 25, 3, 0, tzinfo=KST))
    assert session.regular_start == datetime(2026, 3, 24, 22, 30, tzinfo=KST)


def test_us_market_session_holiday_payload():
    session = parse_market_session(
        {"today": {"date": "2026-07-03", "regularMarket": None}},
        MarketCountry.US,
        entry_cutoff_minutes=30,
    )

    assert not session.orders_open(datetime(2026, 7, 3, 23, 0, tzinfo=KST))
