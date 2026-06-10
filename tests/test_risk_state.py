from __future__ import annotations

from datetime import date
from decimal import Decimal

from toss_bot.config import RiskSettings
from toss_bot.db import BotRepository, init_db
from toss_bot.risk import RiskManager, RiskState


def test_risk_state_persists_daily_halt_across_restart(tmp_path):
    repository = BotRepository(init_db(f"sqlite:///{tmp_path / 'risk.sqlite3'}"))
    day = date(2026, 6, 10)
    iso = day.isocalendar()
    state = RiskState(
        start_day_equity=Decimal("1000000"),
        start_week_equity=Decimal("1000000"),
        peak_equity=Decimal("1000000"),
        current_equity=Decimal("1000000"),
        trading_day=day,
        iso_year=iso.year,
        iso_week=iso.week,
    )
    risk = RiskManager(RiskSettings(daily_loss_limit_pct=0.03), state)
    risk.update_equity(Decimal("969000"), day)
    repository.save_risk_state(risk.state)

    loaded = repository.load_risk_state()
    restarted = RiskManager(RiskSettings(daily_loss_limit_pct=0.03), loaded)
    restarted.update_equity(Decimal("970000"), day)

    allowed, reason = restarted.can_enter("005930", Decimal("500000"), max_positions=8)
    assert not allowed
    assert reason == "daily loss limit reached"


def test_risk_state_resets_daily_halt_on_new_trading_day():
    previous_day = date(2026, 6, 10)
    next_day = date(2026, 6, 11)
    iso = previous_day.isocalendar()
    state = RiskState(
        start_day_equity=Decimal("1000000"),
        start_week_equity=Decimal("1000000"),
        peak_equity=Decimal("1000000"),
        current_equity=Decimal("969000"),
        trading_day=previous_day,
        iso_year=iso.year,
        iso_week=iso.week,
        halted_reason="daily loss limit reached",
    )
    risk = RiskManager(RiskSettings(daily_loss_limit_pct=0.03), state)

    risk.update_equity(Decimal("970000"), next_day)

    allowed, reason = risk.can_enter("005930", Decimal("500000"), max_positions=8)
    assert allowed
    assert reason == "ok"
    assert risk.state.start_day_equity == Decimal("970000")
