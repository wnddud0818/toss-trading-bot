from __future__ import annotations

from decimal import Decimal

from toss_bot.config import CostSettings, ExecutionSettings
from toss_bot.execution import ExecutionPlanner
from toss_bot.models import MarketCountry, OrderSide, OrderType, Signal


class TossMarketStub:
    def __init__(self, orderbook=None, price_limit=None):
        self.orderbook = orderbook or {
            "asks": [{"price": "10050", "volume": "1000"}, {"price": "10100", "volume": "1000"}],
            "bids": [{"price": "10000", "volume": "1000"}, {"price": "9950", "volume": "1000"}],
        }
        self.price_limit = price_limit or {"upperLimitPrice": "13000", "lowerLimitPrice": "7000"}
        self.price_limit_calls = 0

    def get_orderbook(self, symbol):
        return self.orderbook

    def get_price_limit(self, symbol):
        self.price_limit_calls += 1
        return self.price_limit


def buy_signal(price: str = "10000", quantity: str = "100", symbol: str = "000001") -> Signal:
    return Signal(symbol, OrderSide.BUY, OrderType.LIMIT, Decimal(quantity), Decimal(price), "test")


def kr_planner(execution: ExecutionSettings, stub: TossMarketStub, costs: CostSettings | None = None):
    return ExecutionPlanner(execution, costs or CostSettings(), stub, MarketCountry.KR)


def test_execution_planner_accepts_liquid_entry_and_aligns_tick():
    planner = kr_planner(ExecutionSettings(max_entry_spread_bps=60), TossMarketStub())

    plan = planner.plan(buy_signal(price="10100"), urgent=False)

    assert plan.accepted
    assert plan.order is not None
    assert plan.order.price == Decimal("10050")
    assert plan.order.quantity == Decimal("100")


def test_execution_planner_rejects_wide_entry_spread():
    stub = TossMarketStub(orderbook={
        "asks": [{"price": "10500", "volume": "1000"}],
        "bids": [{"price": "10000", "volume": "1000"}],
    })
    planner = kr_planner(ExecutionSettings(max_entry_spread_bps=25), stub)

    plan = planner.plan(buy_signal(), urgent=False)

    assert not plan.accepted
    assert "spread too wide" in plan.reason


def test_execution_planner_rejects_upper_limit_chase():
    stub = TossMarketStub(price_limit={"upperLimitPrice": "10100", "lowerLimitPrice": "7000"})
    planner = kr_planner(ExecutionSettings(max_entry_spread_bps=60), stub)

    plan = planner.plan(buy_signal(price="10020"), urgent=False)

    assert not plan.accepted
    assert plan.reason == "entry too close to upper price limit"


def test_execution_planner_caps_quantity_by_orderbook_participation():
    stub = TossMarketStub(orderbook={
        "asks": [{"price": "10050", "volume": "100"}],
        "bids": [{"price": "10000", "volume": "1000"}],
    })
    planner = kr_planner(
        ExecutionSettings(max_entry_spread_bps=60, max_chase_bps=100, max_orderbook_participation=0.25),
        stub,
        CostSettings(min_order_amount=1000),
    )

    plan = planner.plan(buy_signal(quantity="1000"), urgent=False)

    assert plan.accepted
    assert plan.order is not None
    assert plan.order.quantity == Decimal("25")


def test_us_planner_skips_price_limits_and_uses_cent_ticks():
    stub = TossMarketStub(orderbook={
        "asks": [{"price": "187.43", "volume": "5000"}],
        "bids": [{"price": "187.40", "volume": "5000"}],
    })
    planner = ExecutionPlanner(
        ExecutionSettings(max_entry_spread_bps=15, max_chase_bps=100),
        CostSettings(min_order_amount=500),
        stub,
        MarketCountry.US,
    )

    plan = planner.plan(buy_signal(price="187.50", quantity="100", symbol="AAPL"), urgent=False)

    assert plan.accepted
    assert plan.order is not None
    assert plan.order.price == Decimal("187.43")
    assert stub.price_limit_calls == 0
