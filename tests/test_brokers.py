from __future__ import annotations

from decimal import Decimal

from toss_bot.brokers import LiveBroker, PaperBroker
from toss_bot.config import Settings
from toss_bot.db import BotRepository, init_db
from toss_bot.models import OrderRequest, OrderSide, OrderType, RunMode


def test_paper_broker_fills_without_toss_api(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'paper.sqlite3'}")
    repository = BotRepository(init_db(settings.database_url))
    broker = PaperBroker(settings, repository)

    result = broker.place_order(
        OrderRequest(
            symbol="000001",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("10"),
            price=Decimal("10000"),
        ),
        reason="test",
    )

    assert result.status == "FILLED"
    assert broker.positions()[0].symbol == "000001"


def test_live_broker_requires_double_lock():
    settings = Settings(mode=RunMode.LIVE, enable_live_trading=False)

    try:
        LiveBroker(settings, toss_client=object())
    except RuntimeError as exc:
        assert "ENABLE_LIVE_TRADING" in str(exc)
    else:
        raise AssertionError("LiveBroker should be locked")
