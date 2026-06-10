from __future__ import annotations

from datetime import date
from pathlib import Path

from .config import Settings
from .db import BotRepository


class ReportWriter:
    def __init__(self, settings: Settings, repository: BotRepository):
        self.settings = settings
        self.repository = repository
        self.reports_dir = Path(settings.reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def write_daily_report(self, report_date: date) -> Path:
        trades = self.repository.latest_trades(500)
        orders = self.repository.latest_order_audits(500)
        matching = [trade for trade in trades if trade.ts.date() == report_date]
        matching_orders = [order for order in orders if order.ts.date() == report_date]
        lines = [
            f"# Daily Trading Report {report_date.isoformat()}",
            "",
            f"- Trades: {len(matching)}",
            f"- Orders: {len(matching_orders)}",
            "",
            "| Time | Mode | Symbol | Side | Qty | Price | Commission | Tax | Reason |",
            "|---|---|---|---:|---:|---:|---:|---:|---|",
        ]
        for trade in reversed(matching):
            lines.append(
                "| "
                + " | ".join(
                    [
                        trade.ts.strftime("%H:%M:%S"),
                        trade.mode,
                        trade.symbol,
                        trade.side,
                        str(trade.quantity),
                        str(trade.price),
                        str(trade.commission),
                        str(trade.tax),
                        trade.reason,
                    ]
                )
                + " |"
            )
        lines.extend(
            [
                "",
                "## Order Audit",
                "",
                "| Time | Mode | Order ID | Client ID | Symbol | Side | Status | Qty | Price | Filled | Avg Price | Reason |",
                "|---|---|---|---|---|---|---|---:|---:|---:|---:|---|",
            ]
        )
        for order in reversed(matching_orders):
            lines.append(
                "| "
                + " | ".join(
                    [
                        order.ts.strftime("%H:%M:%S"),
                        order.mode,
                        order.order_id,
                        order.client_order_id or "",
                        order.symbol,
                        order.side,
                        order.status,
                        str(order.quantity),
                        str(order.price or ""),
                        str(order.filled_quantity),
                        str(order.average_price or ""),
                        order.reason,
                    ]
                )
                + " |"
            )
        path = self.reports_dir / f"{report_date.isoformat()}.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path
