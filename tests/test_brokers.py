from __future__ import annotations

from decimal import Decimal

from toss_bot.brokers import LiveBroker, PaperBroker
from toss_bot.config import RiskSettings, Settings
from toss_bot.db import BotRepository, init_db
from toss_bot.models import Currency, OrderRequest, OrderSide, OrderType, RunMode
from toss_bot.toss_client import TossApiError


class FakeFx:
    def __init__(self, rate: str = "1400"):
        self.rate = Decimal(rate)

    def usd_krw(self) -> Decimal:
        return self.rate

    def to_krw(self, amount: Decimal, currency: Currency) -> Decimal:
        return amount if currency == Currency.KRW else amount * self.rate

    def from_krw(self, amount: Decimal, currency: Currency) -> Decimal:
        return amount if currency == Currency.KRW else amount / self.rate


def test_paper_broker_fills_without_toss_api(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'paper.sqlite3'}")
    repository = BotRepository(init_db(settings.database_url))
    broker = PaperBroker(settings, repository, FakeFx())

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


def test_paper_broker_settles_us_orders_in_usd(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'paper.sqlite3'}")
    repository = BotRepository(init_db(settings.database_url))
    broker = PaperBroker(settings, repository, FakeFx())
    krw_before = broker.cash(Currency.KRW)

    broker.place_order(
        OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("10"),
            price=Decimal("100"),
        ),
        reason="test",
    )

    # 미국 주문은 USD 현금에서만 차감되고 원화 잔고는 그대로여야 한다
    assert broker.cash(Currency.KRW) == krw_before
    us_costs = settings.market_profile("US").costs
    slip = Decimal("1") + Decimal(us_costs.slippage_bps) / Decimal("10000")
    fill = (Decimal("100") * slip).quantize(Decimal("0.01"))
    commission = (fill * Decimal("10") * Decimal(str(us_costs.commission_rate))).quantize(Decimal("0.01"))
    expected = Decimal(settings.paper.initial_cash_usd) - fill * Decimal("10") - commission
    assert broker.cash(Currency.USD) == expected


def test_paper_broker_portfolio_value_converts_usd_to_krw(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'paper.sqlite3'}")
    repository = BotRepository(init_db(settings.database_url))
    broker = PaperBroker(settings, repository, FakeFx("1400"))

    value = broker.portfolio_value({})

    expected = Decimal(settings.paper.initial_cash_krw) + Decimal(settings.paper.initial_cash_usd) * Decimal("1400")
    assert value == expected


def test_paper_broker_rejects_disabled_us_market(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'paper.sqlite3'}",
        markets={"US": {"enabled": False}},
    )
    repository = BotRepository(init_db(settings.database_url))
    broker = PaperBroker(settings, repository, FakeFx())

    try:
        broker.place_order(
            OrderRequest("AAPL", OrderSide.BUY, OrderType.LIMIT, Decimal("1"), Decimal("100")),
            reason="test",
        )
    except ValueError as exc:
        assert "US market is disabled" in str(exc)
    else:
        raise AssertionError("disabled US market order should be blocked")


def test_live_broker_requires_double_lock():
    settings = Settings(mode=RunMode.LIVE, enable_live_trading=False)

    try:
        LiveBroker(settings, toss_client=object())
    except RuntimeError as exc:
        assert "ENABLE_LIVE_TRADING" in str(exc)
    else:
        raise AssertionError("LiveBroker should be locked")


class LiveOrderStub:
    def __init__(self, open_orders):
        self.open_orders = open_orders

    def get_open_orders(self, symbol):
        return {"orders": self.open_orders}


def live_settings() -> Settings:
    return Settings(
        mode=RunMode.LIVE,
        enable_live_trading=True,
        risk=RiskSettings(paper_trading_days_completed=20),
    )


def test_live_broker_blocks_same_side_pending_order():
    broker = LiveBroker(
        live_settings(),
        LiveOrderStub([{"symbol": "005930", "side": "BUY", "status": "PENDING"}]),
    )

    try:
        broker.place_order(
            OrderRequest("005930", OrderSide.BUY, OrderType.LIMIT, Decimal("1"), Decimal("70000")),
            reason="test",
        )
    except TossApiError as exc:
        assert exc.code == "same-side-pending-order-exists"
    else:
        raise AssertionError("same-side pending order should block duplicate live buy")


def test_live_broker_caps_us_order_amount_in_krw():
    broker = LiveBroker(live_settings(), LiveOrderStub([]), fx=FakeFx("1400"))

    try:
        # $1,000 × 1,400 = 1,400,000 KRW > 한도 1,000,000 KRW
        broker.place_order(
            OrderRequest("AAPL", OrderSide.BUY, OrderType.LIMIT, Decimal("5"), Decimal("200")),
            reason="test",
        )
    except RuntimeError as exc:
        assert "order amount exceeds" in str(exc)
    else:
        raise AssertionError("US order above the KRW cap should be blocked")


def test_live_broker_rejects_disabled_us_market_before_api_calls():
    settings = live_settings()
    settings.markets["US"].enabled = False
    broker = LiveBroker(settings, LiveOrderStub([]), fx=FakeFx("1400"))

    try:
        broker.place_order(
            OrderRequest("AAPL", OrderSide.BUY, OrderType.LIMIT, Decimal("1"), Decimal("100")),
            reason="test",
        )
    except RuntimeError as exc:
        assert "US market is disabled" in str(exc)
    else:
        raise AssertionError("disabled US market live order should be blocked")


class LiveHoldingStub:
    def __init__(self):
        self.last_price = "72000"

    def get_buying_power(self, currency="KRW"):
        return {"cashBuyingPower": "1000000" if currency == "KRW" else "0"}

    def get_holdings(self):
        return {
            "items": [
                {
                    "marketCountry": "KR",
                    "symbol": "005930",
                    "quantity": "3",
                    "averagePurchasePrice": "70000",
                    "lastPrice": self.last_price,
                }
            ]
        }


def test_live_broker_persists_position_metadata(tmp_path):
    repository = BotRepository(init_db(f"sqlite:///{tmp_path / 'bot.sqlite3'}"))
    toss = LiveHoldingStub()
    broker = LiveBroker(live_settings(), toss, repository)

    first = broker.positions()[0]
    broker.update_high_watermark("005930", Decimal("75000"))
    toss.last_price = "71000"
    second = broker.positions()[0]

    assert second.entry_date == first.entry_date
    assert second.high_watermark == Decimal("75000.0000")


def test_live_broker_marks_portfolio_with_last_price_not_high_watermark(tmp_path):
    repository = BotRepository(init_db(f"sqlite:///{tmp_path / 'bot.sqlite3'}"))
    broker = LiveBroker(live_settings(), LiveHoldingStub(), repository, fx=FakeFx("1400"))
    broker.positions()
    broker.update_high_watermark("005930", Decimal("75000"))

    value = broker.portfolio_value({})

    assert value == Decimal("1000000") + Decimal("3") * Decimal("72000")
