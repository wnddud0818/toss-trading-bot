from __future__ import annotations

from datetime import date
from decimal import Decimal

from toss_bot.cli import main
from toss_bot.db import BotRepository, init_db
from toss_bot.risk import RiskState


def seeded_repository(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'bot.sqlite3'}"
    config = tmp_path / "settings.yaml"
    config.write_text(f"database_url: {db_url}\n", encoding="utf-8")
    repository = BotRepository(init_db(db_url))
    day = date(2026, 6, 10)
    iso = day.isocalendar()
    repository.save_risk_state(
        RiskState(
            start_day_equity=Decimal("1000000"),
            start_week_equity=Decimal("1000000"),
            peak_equity=Decimal("1200000"),
            current_equity=Decimal("1000000"),
            trading_day=day,
            iso_year=iso.year,
            iso_week=iso.week,
        )
    )
    return config, repository


def test_halt_and_resume_cli(tmp_path):
    config, repository = seeded_repository(tmp_path)

    assert main(["--config", str(config), "halt", "--reason", "test halt"]) == 0
    assert repository.load_risk_state().halted_reason == "test halt"

    assert main(["--config", str(config), "resume", "--reset-peak"]) == 0
    state = repository.load_risk_state()
    assert state.halted_reason is None
    assert state.peak_equity == Decimal("1000000")


def test_status_cli_reports_halt(tmp_path, capsys):
    config, repository = seeded_repository(tmp_path)
    main(["--config", str(config), "halt", "--reason", "test halt"])
    capsys.readouterr()

    assert main(["--config", str(config), "status"]) == 0
    output = capsys.readouterr().out
    assert "Halted: test halt" in output
    assert "Mode: paper" in output
