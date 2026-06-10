from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from .config import Settings
from .db import BotRepository
from .utils import money


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
        realized = self._realized_pnl(report_date)
        total_pnl = sum((pnl for _, _, pnl, _ in realized), Decimal("0"))
        wins = sum(1 for _, _, pnl, _ in realized if pnl > 0)
        losses = sum(1 for _, _, pnl, _ in realized if pnl < 0)
        lines = [
            f"# Daily Trading Report {report_date.isoformat()}",
            "",
            f"- Trades: {len(matching)}",
            f"- Orders: {len(matching_orders)}",
            f"- Realized PnL: {money(total_pnl)} KRW (win {wins} / loss {losses})",
            "",
        ]
        if realized:
            lines.extend(
                [
                    "## Realized PnL",
                    "",
                    "| Mode | Symbol | Sells | Realized PnL |",
                    "|---|---|---:|---:|",
                ]
            )
            for mode, symbol, pnl, sell_count in realized:
                lines.append(f"| {mode} | {symbol} | {sell_count} | {money(pnl)} |")
            lines.append("")
        lines.extend(
            [
                "## Trades",
                "",
                "| Time | Mode | Symbol | Side | Qty | Price | Commission | Tax | Reason |",
                "|---|---|---|---:|---:|---:|---:|---:|---|",
            ]
        )
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

    def _realized_pnl(self, report_date: date) -> list[tuple[str, str, Decimal, int]]:
        """평균단가 방식으로 report_date에 실현된 손익을 (mode, symbol)별로 집계한다."""
        books: dict[tuple[str, str], tuple[Decimal, Decimal]] = {}
        realized: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
        sells: dict[tuple[str, str], int] = defaultdict(int)
        for trade in self.repository.trades_ordered():
            if trade.ts.date() > report_date:
                break
            key = (trade.mode, trade.symbol)
            quantity, avg_cost = books.get(key, (Decimal("0"), Decimal("0")))
            if trade.side == "BUY":
                total_cost = avg_cost * quantity + trade.price * trade.quantity + trade.commission
                quantity += trade.quantity
                books[key] = (quantity, total_cost / quantity if quantity > 0 else Decimal("0"))
                continue
            sold = min(trade.quantity, quantity) if quantity > 0 else trade.quantity
            pnl = (trade.price - avg_cost) * sold - trade.commission - trade.tax
            quantity -= sold
            books[key] = (quantity, avg_cost if quantity > 0 else Decimal("0"))
            if trade.ts.date() == report_date:
                realized[key] += pnl
                sells[key] += 1
        return [(key[0], key[1], realized[key], sells[key]) for key in sorted(realized)]
