from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum


class RunMode(StrEnum):
    PAPER = "paper"
    LIVE = "live"


class MarketCountry(StrEnum):
    KR = "KR"
    US = "US"


class Currency(StrEnum):
    KRW = "KRW"
    USD = "USD"


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class UniverseCandidate:
    symbol: str
    name: str
    market: str
    trading_value: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class RankedCandidate:
    symbol: str
    name: str
    market: str
    score: Decimal
    trading_value: Decimal
    volatility: Decimal


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: Decimal
    entry_price: Decimal
    entry_date: date
    high_watermark: Decimal


@dataclass(frozen=True)
class Signal:
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    limit_price: Decimal | None
    reason: str


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Decimal | None = None
    client_order_id: str | None = None
    time_in_force: str = "DAY"


@dataclass(frozen=True)
class OrderResult:
    order_id: str
    client_order_id: str | None
    symbol: str
    side: OrderSide
    status: str
    filled_quantity: Decimal
    average_price: Decimal | None
