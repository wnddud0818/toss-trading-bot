from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from toss_bot.config import Settings
from toss_bot.db import BotRepository, init_db
from toss_bot.models import OrderSide
from toss_bot.reports import ReportWriter
from toss_bot.utils import KST


def test_daily_report_includes_realized_pnl(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'reports.sqlite3'}",
        reports_dir=str(tmp_path / "reports"),
    )
    repository = BotRepository(init_db(settings.database_url))
    repository.record_trade(
        ts=datetime(2026, 6, 9, 10, 0, tzinfo=KST),
        mode="paper",
        symbol="000001",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        price=Decimal("100"),
        commission=Decimal("0"),
        tax=Decimal("0"),
        reason="entry",
    )
    repository.record_trade(
        ts=datetime(2026, 6, 10, 10, 0, tzinfo=KST),
        mode="paper",
        symbol="000001",
        side=OrderSide.SELL,
        quantity=Decimal("10"),
        price=Decimal("110"),
        commission=Decimal("0"),
        tax=Decimal("0"),
        reason="exit",
    )

    path = ReportWriter(settings, repository).write_daily_report(date(2026, 6, 10))
    content = path.read_text(encoding="utf-8")

    assert "Realized PnL: 100 KRW (win 1 / loss 0)" in content
    assert "| paper | 000001 | 1 | 100 |" in content


def test_daily_report_ignores_pnl_realized_on_other_days(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'reports.sqlite3'}",
        reports_dir=str(tmp_path / "reports"),
    )
    repository = BotRepository(init_db(settings.database_url))
    repository.record_trade(
        ts=datetime(2026, 6, 9, 10, 0, tzinfo=KST),
        mode="paper",
        symbol="000001",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        price=Decimal("100"),
        commission=Decimal("0"),
        tax=Decimal("0"),
        reason="entry",
    )
    repository.record_trade(
        ts=datetime(2026, 6, 9, 11, 0, tzinfo=KST),
        mode="paper",
        symbol="000001",
        side=OrderSide.SELL,
        quantity=Decimal("10"),
        price=Decimal("110"),
        commission=Decimal("0"),
        tax=Decimal("0"),
        reason="exit",
    )

    path = ReportWriter(settings, repository).write_daily_report(date(2026, 6, 10))
    content = path.read_text(encoding="utf-8")

    assert "Realized PnL: 0 KRW (win 0 / loss 0)" in content
