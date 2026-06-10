from __future__ import annotations

from decimal import Decimal

from .config import Settings
from .db import BotRepository
from .fx import FxRateProvider
from .markets import currency_for, market_for_symbol, round_money
from .models import Currency, OrderRequest, OrderResult, OrderSide, Position, RunMode
from .toss_client import TossApiError, TossClient
from .utils import dec, extract_items, make_client_order_id, money, now_kst, qty


OPEN_ORDER_STATUSES = {"PENDING", "PARTIAL_FILLED", "PENDING_CANCEL", "PENDING_REPLACE"}


class PaperBroker:
    def __init__(self, settings: Settings, repository: BotRepository, fx: FxRateProvider):
        self.settings = settings
        self.repository = repository
        self.fx = fx

    def cash(self, currency: Currency = Currency.KRW) -> Decimal:
        initial = (
            Decimal(self.settings.paper.initial_cash_krw)
            if currency == Currency.KRW
            else Decimal(self.settings.paper.initial_cash_usd)
        )
        return self.repository.get_cash(currency.value, initial)

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
        """원화 환산 총자산. USD 현금/포지션은 현재 환율로 환산한다."""
        latest_prices = latest_prices or {}
        usd_krw = self.fx.usd_krw()
        equity = self.cash(Currency.KRW)
        us_enabled = any(str(market) == "US" for market in self.settings.enabled_markets())
        if us_enabled:
            equity += self.cash(Currency.USD) * usd_krw
        for position in self.positions():
            mark = latest_prices.get(position.symbol, position.entry_price)
            value = position.quantity * mark
            if currency_for(market_for_symbol(position.symbol)) == Currency.USD:
                value *= usd_krw
            equity += value
        return money(equity)

    def place_order(self, order: OrderRequest, reason: str = "") -> OrderResult:
        if order.price is None:
            raise ValueError("PaperBroker requires price for simulated fills")
        market = market_for_symbol(order.symbol)
        currency = currency_for(market)
        costs = self.settings.market_profile(market).costs
        fill_price = self._fill_price(order, costs, currency)
        commission, fee = self._costs(order.side, order.quantity, fill_price, costs, currency)
        if order.side == OrderSide.BUY:
            self._buy(order, fill_price, commission, currency)
        else:
            self._sell(order, fill_price, commission, fee, currency)
        client_order_id = order.client_order_id or make_client_order_id(order.symbol, order.side, "paper")
        self.repository.record_trade(
            ts=now_kst(),
            mode=RunMode.PAPER.value,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            commission=commission,
            tax=fee,
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

    def _buy(self, order: OrderRequest, fill_price: Decimal, commission: Decimal, currency: Currency) -> None:
        cash = self.cash(currency)
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
        self.repository.set_cash(currency.value, round_money(cash - total, currency))
        self.repository.upsert_position(position)

    def _sell(
        self,
        order: OrderRequest,
        fill_price: Decimal,
        commission: Decimal,
        fee: Decimal,
        currency: Currency,
    ) -> None:
        positions = {position.symbol: position for position in self.positions()}
        position = positions.get(order.symbol)
        if position is None or order.quantity > position.quantity:
            raise ValueError("paper sellable quantity is insufficient")
        proceeds = order.quantity * fill_price - commission - fee
        remaining = position.quantity - order.quantity
        self.repository.set_cash(currency.value, round_money(self.cash(currency) + proceeds, currency))
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

    def _fill_price(self, order: OrderRequest, costs, currency: Currency) -> Decimal:
        assert order.price is not None
        slip = dec(costs.slippage_bps) / Decimal("10000")
        if order.side == OrderSide.BUY:
            return round_money(order.price * (Decimal("1") + slip), currency)
        return round_money(order.price * (Decimal("1") - slip), currency)

    def _costs(
        self,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        costs,
        currency: Currency,
    ) -> tuple[Decimal, Decimal]:
        gross = quantity * price
        commission = round_money(gross * dec(costs.commission_rate), currency)
        fee = round_money(gross * dec(costs.sell_fee_rate), currency) if side == OrderSide.SELL else Decimal("0")
        return commission, fee


class LiveBroker:
    def __init__(
        self,
        settings: Settings,
        toss_client: TossClient,
        repository: BotRepository | None = None,
        fx: FxRateProvider | None = None,
    ):
        self.settings = settings
        self.toss_client = toss_client
        self.repository = repository
        self.fx = fx
        self._last_prices: dict[str, Decimal] = {}
        self._allowed_countries = {str(market) for market in settings.enabled_markets()}
        if settings.mode != RunMode.LIVE:
            raise RuntimeError("settings.mode must be live for LiveBroker")
        if not settings.enable_live_trading:
            raise RuntimeError("ENABLE_LIVE_TRADING=true is required for live trading")
        if settings.risk.paper_trading_days_completed < settings.risk.min_paper_trading_days:
            raise RuntimeError("paper trading gate is not satisfied")

    def place_order(self, order: OrderRequest, reason: str = "") -> OrderResult:
        market = market_for_symbol(order.symbol)
        currency = currency_for(market)
        estimated_amount = (order.price or Decimal("0")) * order.quantity
        estimated_krw = estimated_amount if currency == Currency.KRW else estimated_amount * self._usd_krw()
        if estimated_krw > Decimal(self.settings.risk.max_live_order_amount_krw):
            raise RuntimeError("live order amount exceeds configured cap")
        self._assert_no_conflicting_open_order(order)
        if order.side == OrderSide.BUY:
            cash = self.cash(currency)
            commission_rate = dec(self.settings.market_profile(market).costs.commission_rate)
            required = estimated_amount * (Decimal("1") + commission_rate)
            if required > cash:
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

    def cash(self, currency: Currency = Currency.KRW) -> Decimal:
        buying_power = self.toss_client.get_buying_power(currency.value)
        return dec(buying_power.get("cashBuyingPower", 0))

    def positions(self) -> list[Position]:
        holdings = self.toss_client.get_holdings()
        items = extract_items(holdings, "items")
        today = now_kst().date()
        positions: list[Position] = []
        active_symbols: set[str] = set()
        for item in items:
            symbol = item.get("symbol")
            if not symbol:
                continue
            country = item.get("marketCountry") or str(market_for_symbol(symbol))
            if country not in self._allowed_countries:
                continue
            quantity = dec(item.get("quantity", 0))
            if quantity <= 0:
                continue
            entry_price = dec(item.get("averagePurchasePrice", item.get("lastPrice", 0)))
            last_price = dec(item.get("lastPrice", entry_price))
            active_symbols.add(symbol)
            self._last_prices[symbol] = last_price
            entry_date = today
            high_watermark = max(entry_price, last_price)
            if self.repository is not None:
                meta = self.repository.get_position_meta(symbol)
                if meta is not None:
                    entry_date, stored_high = meta
                    high_watermark = max(stored_high, high_watermark)
                self.repository.upsert_position_meta(symbol, entry_date, high_watermark)
            positions.append(
                Position(
                    symbol=symbol,
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
        usd_krw = self._usd_krw()
        equity = self.cash(Currency.KRW)
        if "US" in self._allowed_countries and self.fx is not None:
            equity += self.cash(Currency.USD) * usd_krw
        for position in self.positions():
            # high_watermark로 마킹하면 자산이 과대평가되어 손실 한도 감지가 늦어진다.
            mark = latest_prices.get(position.symbol) or self._last_prices.get(position.symbol) or position.entry_price
            value = position.quantity * mark
            if currency_for(market_for_symbol(position.symbol)) == Currency.USD:
                value *= usd_krw
            equity += value
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

    def _usd_krw(self) -> Decimal:
        if self.fx is None:
            return Decimal("0")
        return self.fx.usd_krw()

    def _assert_no_conflicting_open_order(self, order: OrderRequest) -> None:
        open_orders = self.toss_client.get_open_orders(order.symbol)
        orders = extract_items(open_orders, "orders")
        for open_order in orders:
            if open_order.get("status") not in OPEN_ORDER_STATUSES:
                continue
            side = open_order.get("side")
            if side == order.side.value:
                raise TossApiError(422, "same-side-pending-order-exists", "Same-side open order exists")
            opposite = OrderSide.SELL if order.side == OrderSide.BUY else OrderSide.BUY
            if side == opposite.value:
                raise TossApiError(422, "opposite-pending-order-exists", "Opposite open order exists")
