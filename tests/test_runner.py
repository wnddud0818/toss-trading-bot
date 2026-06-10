from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import toss_bot.runner as runner
from toss_bot.config import Settings
from toss_bot.db import BotRepository, init_db
from toss_bot.models import Position
from toss_bot.notifications import DiscordNotifier
from toss_bot.runner import TradingBot
from toss_bot.utils import KST


class TossRunnerStub:
    def get_kr_market_calendar(self):
        return {
            "today": {
                "integrated": {
                    "regularMarket": {
                        "startTime": "2026-06-10T09:00:00+09:00",
                        "singlePriceAuctionStartTime": "2026-06-10T15:20:00+09:00",
                        "endTime": "2026-06-10T15:30:00+09:00",
                    }
                }
            }
        }


class NullNotifier(DiscordNotifier):
    def __init__(self):
        pass

    def send(self, message: str) -> None:
        self.last_message = message


class UnavailableMarketFilter:
    def risk_on(self, as_of):
        return None


class RiskOnMarketFilter:
    def risk_on(self, as_of):
        return True


class TossMarketDataStub(TossRunnerStub):
    def get_candles(self, symbol, interval, count):
        return {
            "candles": [
                {
                    "timestamp": "2026-06-10T09:59:00+09:00",
                    "openPrice": "9000",
                    "highPrice": "9050",
                    "lowPrice": "8950",
                    "closePrice": "9000",
                    "volume": "1000",
                }
            ]
        }

    def get_prices(self, symbols):
        return {"prices": [{"symbol": symbol, "lastPrice": "9000"} for symbol in symbols]}

    def get_orderbook(self, symbol):
        return {
            "asks": [{"price": "9010", "volume": "100000"}],
            "bids": [{"price": "9000", "volume": "100000"}],
        }

    def get_price_limit(self, symbol):
        return {"upperLimitPrice": "13000", "lowerLimitPrice": "7000"}


class ClosedMarketStub:
    def get_kr_market_calendar(self):
        return {"today": {"integrated": {"regularMarket": {}}}}


def test_market_filter_unavailable_does_not_force_risk_off_exits(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "now_kst", lambda: datetime(2026, 6, 10, 10, 0, tzinfo=KST))
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'runner.sqlite3'}")
    repository = BotRepository(init_db(settings.database_url))
    bot = TradingBot(settings, repository, TossRunnerStub(), NullNotifier())
    bot.market_filter = UnavailableMarketFilter()
    seen = []

    def fake_process_exits(positions, today, market_ok):
        seen.append(market_ok)

    bot._process_exits = fake_process_exits

    bot.market_loop_once()

    assert seen == [True]


def test_exit_failure_does_not_block_other_positions(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "now_kst", lambda: datetime(2026, 6, 10, 10, 0, tzinfo=KST))
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'runner.sqlite3'}")
    repository = BotRepository(init_db(settings.database_url))
    bot = TradingBot(settings, repository, TossMarketDataStub(), NullNotifier())
    repository.upsert_position(Position("000001", Decimal("10"), Decimal("10000"), date(2026, 6, 9), Decimal("10000")))
    repository.upsert_position(Position("000002", Decimal("10"), Decimal("10000"), date(2026, 6, 9), Decimal("10000")))
    placed = []
    original_place_order = bot.broker.place_order

    def flaky_place_order(order, reason=""):
        if order.symbol == "000001":
            raise RuntimeError("boom")
        placed.append(order.symbol)
        return original_place_order(order, reason=reason)

    monkeypatch.setattr(bot.broker, "place_order", flaky_place_order)
    positions = {position.symbol: position for position in bot.broker.positions()}

    bot._process_exits(positions, date(2026, 6, 10), True)

    assert placed == ["000002"]


def test_close_policy_skipped_on_non_business_day(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "now_kst", lambda: datetime(2026, 6, 13, 15, 25, tzinfo=KST))
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'runner.sqlite3'}")
    repository = BotRepository(init_db(settings.database_url))
    bot = TradingBot(settings, repository, ClosedMarketStub(), NullNotifier())

    def fail_positions():
        raise AssertionError("positions should not be queried when the market is closed")

    monkeypatch.setattr(bot.broker, "positions", fail_positions)

    bot.close_policy()


def test_market_loop_adopts_externally_stored_halt(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "now_kst", lambda: datetime(2026, 6, 10, 10, 0, tzinfo=KST))
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'runner.sqlite3'}")
    repository = BotRepository(init_db(settings.database_url))
    bot = TradingBot(settings, repository, TossRunnerStub(), NullNotifier())
    bot.market_filter = RiskOnMarketFilter()
    state = repository.load_risk_state()
    state.halted_reason = "manual halt"
    repository.save_risk_state(state)

    bot.market_loop_once()

    assert bot.risk.state.halted_reason == "manual halt"
    assert "trading halted: manual halt" in bot.notifier.last_message
