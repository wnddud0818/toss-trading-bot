from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .config import ExecutionSettings, RiskSettings
from .models import OrderRequest, OrderSide, OrderType, Signal
from .toss_client import TossClient
from .utils import align_kr_price, dec, money, qty


@dataclass(frozen=True)
class ExecutionPlan:
    accepted: bool
    reason: str
    order: OrderRequest | None = None
    spread_bps: Decimal | None = None


class ExecutionPlanner:
    def __init__(self, settings: ExecutionSettings, risk_settings: RiskSettings, toss_client: TossClient):
        self.settings = settings
        self.risk_settings = risk_settings
        self.toss_client = toss_client

    def plan(self, signal: Signal, *, urgent: bool = False) -> ExecutionPlan:
        if signal.limit_price is None:
            return ExecutionPlan(False, "limit price is required")
        orderbook = self.toss_client.get_orderbook(signal.symbol)
        price_limit = self.toss_client.get_price_limit(signal.symbol)
        asks = _levels(orderbook.get("asks", []), reverse=False)
        bids = _levels(orderbook.get("bids", []), reverse=True)
        if not asks or not bids:
            return ExecutionPlan(False, "empty orderbook")
        best_ask = asks[0][0]
        best_bid = bids[0][0]
        mid = (best_ask + best_bid) / Decimal("2")
        if mid <= 0:
            return ExecutionPlan(False, "invalid mid price")
        spread_bps = (best_ask - best_bid) / mid * Decimal("10000")
        max_spread = Decimal(self.settings.max_exit_spread_bps if urgent else self.settings.max_entry_spread_bps)
        if spread_bps > max_spread:
            return ExecutionPlan(False, f"spread too wide: {spread_bps:.2f}bps", spread_bps=spread_bps)

        limit_guard = self._price_limit_guard(signal, price_limit)
        if limit_guard:
            return ExecutionPlan(False, limit_guard, spread_bps=spread_bps)

        if signal.side == OrderSide.BUY:
            return self._buy_plan(signal, asks, spread_bps)
        return self._sell_plan(signal, bids, spread_bps, urgent=urgent)

    def _buy_plan(self, signal: Signal, asks: list[tuple[Decimal, Decimal]], spread_bps: Decimal) -> ExecutionPlan:
        assert signal.limit_price is not None
        max_chase_price = signal.limit_price * (Decimal("1") + Decimal(self.settings.max_chase_bps) / Decimal("10000"))
        executable = [(price, volume) for price, volume in asks if price <= max_chase_price]
        if not executable:
            return ExecutionPlan(False, "best ask exceeds chase limit", spread_bps=spread_bps)
        available = sum(volume for _, volume in executable)
        capped_quantity = qty(min(signal.quantity, available * dec(self.settings.max_orderbook_participation)))
        if capped_quantity <= 0:
            return ExecutionPlan(False, "insufficient ask depth", spread_bps=spread_bps)
        best_price = executable[0][0]
        if capped_quantity * best_price < Decimal(self.risk_settings.min_order_amount_krw):
            return ExecutionPlan(False, "order amount below minimum", spread_bps=spread_bps)
        price = align_kr_price(best_price, side=OrderSide.BUY.value)
        return ExecutionPlan(
            True,
            "accepted",
            OrderRequest(signal.symbol, signal.side, OrderType.LIMIT, capped_quantity, price),
            spread_bps,
        )

    def _sell_plan(
        self,
        signal: Signal,
        bids: list[tuple[Decimal, Decimal]],
        spread_bps: Decimal,
        *,
        urgent: bool,
    ) -> ExecutionPlan:
        assert signal.limit_price is not None
        min_price = signal.limit_price * (Decimal("1") - Decimal(self.settings.max_chase_bps) / Decimal("10000"))
        executable = bids if urgent else [(price, volume) for price, volume in bids if price >= min_price]
        if not executable:
            return ExecutionPlan(False, "best bid below chase limit", spread_bps=spread_bps)
        available = sum(volume for _, volume in executable)
        capped_quantity = qty(min(signal.quantity, available * dec(self.settings.max_orderbook_participation)))
        if capped_quantity <= 0:
            return ExecutionPlan(False, "insufficient bid depth", spread_bps=spread_bps)
        price = align_kr_price(executable[0][0], side=OrderSide.SELL.value)
        return ExecutionPlan(
            True,
            "accepted",
            OrderRequest(signal.symbol, signal.side, OrderType.LIMIT, capped_quantity, price),
            spread_bps,
        )

    def _price_limit_guard(self, signal: Signal, price_limit: dict) -> str | None:
        assert signal.limit_price is not None
        upper = price_limit.get("upperLimitPrice")
        lower = price_limit.get("lowerLimitPrice")
        buffer = dec(self.settings.price_limit_buffer_pct)
        if signal.side == OrderSide.BUY and upper is not None:
            upper_price = dec(upper)
            if signal.limit_price >= upper_price * (Decimal("1") - buffer):
                return "entry too close to upper price limit"
        if signal.side == OrderSide.SELL and lower is not None:
            lower_price = dec(lower)
            if signal.limit_price < lower_price:
                return "sell price is below lower price limit"
        return None


def _levels(raw: list[dict], *, reverse: bool) -> list[tuple[Decimal, Decimal]]:
    levels = [(dec(item["price"]), dec(item["volume"])) for item in raw if dec(item.get("volume", 0)) > 0]
    return sorted(levels, key=lambda level: level[0], reverse=reverse)
