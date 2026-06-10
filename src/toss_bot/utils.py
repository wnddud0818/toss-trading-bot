from __future__ import annotations

import uuid
import logging
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from datetime import datetime
from decimal import Decimal, ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR
from io import StringIO
from zoneinfo import ZoneInfo

from .models import Candle, OrderSide

KST = ZoneInfo("Asia/Seoul")


def dec(value: object) -> Decimal:
    return Decimal(str(value))


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_DOWN)


def qty(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_DOWN)


def kr_tick_size(price: Decimal) -> Decimal:
    if price < Decimal("2000"):
        return Decimal("1")
    if price < Decimal("5000"):
        return Decimal("5")
    if price < Decimal("20000"):
        return Decimal("10")
    if price < Decimal("50000"):
        return Decimal("50")
    if price < Decimal("200000"):
        return Decimal("100")
    if price < Decimal("500000"):
        return Decimal("500")
    return Decimal("1000")


def align_kr_price(price: Decimal, *, side: str) -> Decimal:
    tick = kr_tick_size(price)
    rounding = ROUND_CEILING if side == "BUY" else ROUND_FLOOR
    ticks = (price / tick).to_integral_value(rounding=rounding)
    return ticks * tick


def make_client_order_id(symbol: str, side: OrderSide, prefix: str = "tb") -> str:
    token = uuid.uuid4().hex[:12]
    compact = f"{prefix}-{symbol}-{side.value[0]}-{token}"
    return compact[:36]


def extract_items(payload: object, *keys: str) -> list:
    """Toss API 응답이 리스트 그대로 오는 경우와 dict로 감싸져 오는 경우를 모두 흡수한다."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def parse_toss_candle(item: dict) -> Candle:
    return Candle(
        timestamp=datetime.fromisoformat(item["timestamp"]),
        open=dec(item["openPrice"]),
        high=dec(item["highPrice"]),
        low=dec(item["lowPrice"]),
        close=dec(item["closePrice"]),
        volume=dec(item["volume"]),
    )


def now_kst() -> datetime:
    return datetime.now(tz=KST)


@contextmanager
def quiet_external_data_source():
    previous_raise_exceptions = logging.raiseExceptions
    previous_disable_level = logging.root.manager.disable
    logging.raiseExceptions = False
    logging.disable(logging.CRITICAL)
    try:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            yield
    finally:
        logging.disable(previous_disable_level)
        logging.raiseExceptions = previous_raise_exceptions
