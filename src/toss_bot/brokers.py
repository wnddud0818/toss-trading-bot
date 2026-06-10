from __future__ import annotations

from decimal import Decimal

from .config import Settings
from .db import BotRepository
from .models import OrderRequest, OrderResult, OrderSide, Position, RunMode
from .toss_client import TossApiError, TossClient
from .utils import dec, make_client_order_id, money, now_kst, qty


OPEN_ORDER_STATUSES = {"PENDING", "PARTIAL_FILLED", "PENDING_CANCEL", "PENDING_REPLACE"}


class PaperBroker:
    def __init__(self, settings: Settings, repository: BotRepository):
        self.settings = settings
        self.repository = repository

    def cash(self) -> Decimal:
        return self.repository.get_cash(Decimal(self.settings.paper.initial_cash_krw))

    def positions(self) -> list[Position]:
        return self.repository.list_positions()

    def update_high_watermark(self, symbol: str, high_watermark: Decimal) -> None:
        positions = {position.symbol: position for position in self.positions()}
        position = positions.get(symbol)
        if position is None or high_watermark <= position.high_watermark:
            return
        self.repository.upsert_position(
            Position(
                symbol=position.symbol,
                quantity=position.quantity,
                entry_price=position.entry_price,
                entry_date=position.entry_date,
                high_watermark=high_watermark,
            )
        )

    def portfolio_value(self, latest_prices: dict[str, Decimal] | None = None) -> Decimal:
        latest_prices = latest_prices or {}
        equity = self.cash()
        for position in self.positions():
            mark = latest_prices.get(position.symbol, position.entry_price)
            equity += position.quantity * mark
        return money(equity)

    def place_order(self, order: OrderRequest, reason: str = "") -> OrderResult:
        if order.price is None:
            raise ValueError("PaperBroker requires price for simulated fills")
        fill_price = self._fill_price(order)
        commission, tax = self._costs(order.side, order.quantity, fill_price)
        if order.side == OrderSide.BUY:
            self._buy(order, fill_price, commission)
        else:
            self._sell(order, fill_price, commission, tax)
        client_order_id = order.client_order_id or make_client_order_id(order.symbol, order.side, "paper")
        self.repository.record_trade(
            ts=now_kst(),
            mode=RunMode.PAPER.value,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            commission=commission,
            tax=tax,
            reason=reason,
        )
        return OrderResult(
            order_id=f"paper-{client_order_id}",
            client_order_id=client_order_id,
            symbol=order.symbol,
            side=order.side,
            status="FILLED",
            filled_quantity=order.quantity,
            average_price=fill_price,
        )

    def _buy(self, order: OrderRequest, fill_price: Decimal, commission: Decimal) -> None:
        cash = self.cash()
        total = order.quantity * fill_price + commission
        if total > cash:
            raise ValueError("paper buying power is insufficient")
        existing = {position.symbol: position for position in self.positions()}.get(order.symbol)
        if existing:
            new_quantity = existing.quantity + order.quantity
            average_price = ((existing.quantity * existing.entry_price) + (order.quantity * fill_price)) / new_quantity
            position = Position(order.symbol, new_quantity, average_price, existing.entry_date, max(existing.high_watermark, fill_price))
        else:
            position = Position(order.symbol, order.quantity, fill_price, now_kst().date(), fill_price)
        self.repository.set_cash(money(cash - total))
        self.repository.upsert_position(position)

    def _sell(self, order: OrderRequest, fill_price: Decimal, commission: Decimal, tax: Decimal) -> None:
        positions = {position.symbol: position for position in self.positions()}
        position = positions.get(order.symbol)
        if position is None or order.quantity > position.quantity:
            raise ValueError("paper sellable quantity is insufficient")
        proceeds = order.quantity * fill_price - commission - tax
        remaining = position.quantity - order.quantity
        self.repository.set_cash(money(self.cash() + proceeds))
        if remaining <= 0:
            self.repository.delete_position(order.symbol)
        else:
            self.repository.upsert_position(
                Position(
                    symbol=position.symbol,
                    quantity=remaining,
                    entry_price=position.entry_price,
                    entry_date=position.entry_date,
                    high_watermark=max(position.high_watermark, fill_price),
                )
            )

    def _fill_price(self, order: OrderRequest) -> Decimal:
        assert order.price is not None
        slip = dec(self.settings.risk.slippage_bps) / Decimal("10000")
        if order.side == OrderSide.BUY:
            return money(order.price * (Decimal("1") + slip))
        return money(order.price * (Decimal("1") - slip))

    def _costs(self, side: OrderSide, quantity: Decimal, price: Decimal) -> tuple[Decimal, Decimal]:
        gross = quantity * price
        commission = money(gross * dec(self.settings.risk.commission_rate))
        tax = money(gross * dec(self.settings.risk.transaction_tax_rate)) if side == OrderSide.SELL else Decimal("0")
        return commission, tax


class LiveBroker:
    def __init__(self, settings: Settings, toss_client: TossClient, repository: BotRepository | None = None):
        self.settings = settings
        self.toss_client = toss_client
        self.repository = repository
        if settings.mode != RunMode.LIVE:
            raise RuntimeError("settings.mode must be live for LiveBroker")
        if not settings.enable_live_trading:
            raise RuntimeError("ENABLE_LIVE_TRADING=true is required for live trading")
        if settings.risk.paper_trading_days_completed < settings.risk.min_paper_trading_days:
            raise RuntimeError("paper trading gate is not satisfied")

    def place_order(self, order: OrderRequest, reason: str = "") -> OrderResult:
        estimated_amount = (order.price or Decimal("0")) * order.quantity
        if estimated_amount > Decimal(self.settings.risk.max_live_order_amount_krw):
            raise RuntimeError("live order amount exceeds configured cap")
        self._assert_no_conflicting_open_order(order)
        if order.side == OrderSide.BUY:
            buying_power = self.toss_client.get_buying_power("KRW")
            cash = dec(buying_power.get("cashBuyingPower", 0))
            if estimated_amount > cash:
                raise RuntimeError("live buying power is insufficient")
        else:
            sellable = self.toss_client.get_sellable_quantity(order.symbol)
            if order.quantity > qty(dec(sellable.get("sellableQuantity", 0))):
                raise RuntimeError("live sellable quantity is insufficient")
        client_order_id = order.client_order_id or make_client_order_id(order.symbol, order.side, "live")
        result = self.toss_client.create_order(
            OrderRequest(
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                price=order.price,
                client_order_id=client_order_id,
            )
        )
        return OrderResult(
            order_id=result["orderId"],
            client_order_id=result.get("clientOrderId", client_order_id),
            symbol=order.symbol,
            side=order.side,
            status="PENDING",
            filled_quantity=Decimal("0"),
            average_price=None,
        )

    def cash(self) -> Decimal:
        buying_power = self.toss_client.get_buying_power("KRW")
        return dec(buying_power.get("cashBuyingPower", 0))

    def positions(self) -> list[Position]:
        holdings = self.toss_client.get_holdings()
        items = holdings.get("items", holdings if isinstance(holdings, list) else [])
        today = now_kst().date()
        positions: list[Position] = []
        active_symbols: set[str] = set()
        for item in items:
            if item.get("marketCountry") not in (None, "KR"):
                continue
            quantity = dec(item.get("quantity", 0))
            if quantity <= 0:
                continue
            entry_price = dec(item.get("averagePurchasePrice", item.get("lastPrice", 0)))
            last_price = dec(item.get("lastPrice", entry_price))
            active_symbols.add(item["symbol"])
            entry_date = today
            high_watermark = max(entry_price, last_price)
            if self.repository is not None:
                meta = self.repository.get_position_meta(item["symbol"])
                if meta is not None:
                    entry_date, stored_high = meta
                    high_watermark = max(stored_high, high_watermark)
                self.repository.upsert_position_meta(item["symbol"], entry_date, high_watermark)
            positions.append(
                Position(
                    symbol=item["symbol"],
                    quantity=quantity,
                    entry_price=entry_price,
                    entry_date=entry_date,
                    high_watermark=high_watermark,
                )
            )
        if self.repository is not None:
            self.repository.prune_position_meta(active_symbols)
        return positions

    def portfolio_value(self, latest_prices: dict[str, Decimal] | None = None) -> Decimal:
        latest_prices = latest_prices or {}
        equity = self.cash()
        for position in self.positions():
            equity += position.quantity * latest_prices.get(position.symbol, position.high_watermark)
        return money(equity)

    def update_high_watermark(self, symbol: str, high_watermark: Decimal) -> None:
        if self.repository is None:
            return
        meta = self.repository.get_position_meta(symbol)
        entry_date = now_kst().date()
        current_high = Decimal("0")
        if meta is not None:
            entry_date, current_high = meta
        if high_watermark > current_high:
            self.repository.upsert_position_meta(symbol, entry_date, high_watermark)

    def _assert_no_conflicting_open_order(self, order: OrderRequest) -> None:
        open_orders = self.toss_client.get_open_orders(order.symbol)
        orders = open_orders.get("orders", open_orders if isinstance(open_orders, list) else [])
        for open_order in orders:
            if open_order.get("status") not in OPEN_ORDER_STATUSES:
                continue
            side = open_order.get("side")
            if side == order.side.value:
                raise TossApiError(422, "same-side-pending-order-exists", "Same-side open order exists")
            opposite = OrderSide.SELL if order.side == OrderSide.BUY else OrderSide.BUY
            if side == opposite.value:
                raise TossApiError(422, "opposite-pending-order-exists", "Opposite open order exists")
