from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .config import ExecutionSettings
from .toss_client import TossClient
from .utils import KST, extract_items, now_kst


OPEN_ORDER_STATUSES = {"PENDING", "PARTIAL_FILLED", "PENDING_CANCEL", "PENDING_REPLACE"}


@dataclass(frozen=True)
class ReconcileReport:
    open_orders: int
    canceled_orders: int
    kept_orders: int
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"open={self.open_orders} canceled={self.canceled_orders} "
            f"kept={self.kept_orders} errors={len(self.errors)}"
        )


class OrderReconciler:
    def __init__(
        self,
        settings: ExecutionSettings,
        toss_client: TossClient,
        allowed_currencies: set[str] | None = None,
    ):
        self.settings = settings
        self.toss_client = toss_client
        self.allowed_currencies = allowed_currencies or {"KRW", "USD"}

    def reconcile(self, *, cancel_stale: bool | None = None) -> ReconcileReport:
        should_cancel = self.settings.cancel_stale_orders if cancel_stale is None else cancel_stale
        payload = self.toss_client.get_open_orders()
        orders = extract_items(payload, "orders")
        cutoff = now_kst() - timedelta(minutes=self.settings.stale_order_minutes)
        canceled = 0
        kept = 0
        errors: list[str] = []

        for order in orders:
            if order.get("status") not in OPEN_ORDER_STATUSES:
                kept += 1
                continue
            currency = order.get("currency")
            if currency is not None and currency not in self.allowed_currencies:
                kept += 1
                continue
            ordered_at = _parse_ordered_at(order.get("orderedAt"))
            is_stale = ordered_at is not None and ordered_at < cutoff
            if not should_cancel or not is_stale:
                kept += 1
                continue
            order_id = order.get("orderId")
            if not order_id:
                kept += 1
                errors.append(f"missing orderId for {order.get('symbol', 'unknown')}")
                continue
            try:
                self.toss_client.cancel_order(order_id)
                canceled += 1
            except Exception as exc:  # pragma: no cover - defensive logging path
                kept += 1
                errors.append(f"{order_id}: {exc}")

        return ReconcileReport(open_orders=len(orders), canceled_orders=canceled, kept_orders=kept, errors=errors)


def _parse_ordered_at(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=KST)
    return parsed.astimezone(KST)
