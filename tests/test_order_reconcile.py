from __future__ import annotations

from datetime import datetime

import toss_bot.order_reconcile as order_reconcile
from toss_bot.config import ExecutionSettings
from toss_bot.order_reconcile import OrderReconciler
from toss_bot.utils import KST


class TossOrderStub:
    def __init__(self):
        self.canceled: list[str] = []

    def get_open_orders(self):
        return {
            "orders": [
                {
                    "orderId": "old-order",
                    "symbol": "005930",
                    "side": "BUY",
                    "status": "PENDING",
                    "currency": "KRW",
                    "orderedAt": "2026-06-10T09:00:00+09:00",
                },
                {
                    "orderId": "fresh-order",
                    "symbol": "000660",
                    "side": "BUY",
                    "status": "PENDING",
                    "currency": "KRW",
                    "orderedAt": "2026-06-10T09:59:00+09:00",
                },
            ]
        }

    def cancel_order(self, order_id):
        self.canceled.append(order_id)
        return {"orderId": order_id}


def test_reconciler_cancels_stale_kr_open_orders(monkeypatch):
    monkeypatch.setattr(order_reconcile, "now_kst", lambda: datetime(2026, 6, 10, 10, 0, tzinfo=KST))
    toss = TossOrderStub()
    reconciler = OrderReconciler(ExecutionSettings(stale_order_minutes=3), toss)

    report = reconciler.reconcile(cancel_stale=True)

    assert report.open_orders == 2
    assert report.canceled_orders == 1
    assert report.kept_orders == 1
    assert toss.canceled == ["old-order"]
