from __future__ import annotations

from datetime import datetime

import toss_bot.runner as runner
from toss_bot.config import Settings
from toss_bot.db import BotRepository, init_db
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
