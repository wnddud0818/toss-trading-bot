from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .config import RiskSettings
from .models import Position
from .utils import dec, money


@dataclass
class RiskState:
    start_day_equity: Decimal
    start_week_equity: Decimal
    peak_equity: Decimal
    current_equity: Decimal
    trading_day: date | None = None
    iso_year: int | None = None
    iso_week: int | None = None
    halted_reason: str | None = None


@dataclass
class RiskManager:
    settings: RiskSettings
    state: RiskState
    positions: dict[str, Position] = field(default_factory=dict)

    def update_equity(self, equity: Decimal, as_of: date | None = None) -> None:
        if as_of is not None:
            self._roll_periods(as_of, equity)
        self.state.current_equity = equity
        if equity > self.state.peak_equity:
            self.state.peak_equity = equity
        self._refresh_halt()

    def can_enter(self, symbol: str, cash: Decimal, max_positions: int | None = None) -> tuple[bool, str]:
        self._refresh_halt()
        if self.state.halted_reason:
            return False, self.state.halted_reason
        if symbol in self.positions:
            return False, "already holding symbol"
        if max_positions is not None and len(self.positions) >= max_positions:
            return False, "max positions reached"
        min_cash = self.state.current_equity * dec(self.settings.min_cash_weight)
        if cash <= min_cash:
            return False, "minimum cash reserve reached"
        return True, "ok"

    def position_budget(
        self,
        cash: Decimal,
        volatility: Decimal | None = None,
        stop_loss_pct: Decimal | None = None,
    ) -> Decimal:
        gross_budget = self.state.current_equity * dec(self.settings.max_symbol_weight)
        if stop_loss_pct is not None and stop_loss_pct > 0:
            risk_capped_budget = self.state.current_equity * dec(self.settings.max_entry_risk_pct) / stop_loss_pct
            gross_budget = min(gross_budget, risk_capped_budget)
        if volatility is not None and volatility > 0:
            vol_scale = dec(self.settings.target_position_volatility_pct) / volatility
            gross_budget *= min(Decimal("1"), max(Decimal("0.25"), vol_scale))
        min_cash = self.state.current_equity * dec(self.settings.min_cash_weight)
        spendable_cash = max(cash - min_cash, Decimal("0"))
        budget = money(min(gross_budget, spendable_cash))
        if budget < Decimal(self.settings.min_order_amount_krw):
            return Decimal("0")
        return budget

    def _roll_periods(self, as_of: date, equity: Decimal) -> None:
        iso = as_of.isocalendar()
        if self.state.trading_day is None:
            self.state.trading_day = as_of
        elif self.state.trading_day != as_of:
            self.state.trading_day = as_of
            self.state.start_day_equity = equity
            if self.state.halted_reason == "daily loss limit reached":
                self.state.halted_reason = None

        if self.state.iso_year is None or self.state.iso_week is None:
            self.state.iso_year = iso.year
            self.state.iso_week = iso.week
        elif self.state.iso_year != iso.year or self.state.iso_week != iso.week:
            self.state.iso_year = iso.year
            self.state.iso_week = iso.week
            self.state.start_week_equity = equity
            if self.state.halted_reason == "weekly loss limit reached":
                self.state.halted_reason = None

    def _refresh_halt(self) -> None:
        if self.state.halted_reason:
            return
        if self.state.start_day_equity <= 0 or self.state.start_week_equity <= 0 or self.state.peak_equity <= 0:
            return
        day_loss = (self.state.current_equity / self.state.start_day_equity) - Decimal("1")
        week_loss = (self.state.current_equity / self.state.start_week_equity) - Decimal("1")
        drawdown = Decimal("1") - (self.state.current_equity / self.state.peak_equity)
        if day_loss <= -dec(self.settings.daily_loss_limit_pct):
            self.state.halted_reason = "daily loss limit reached"
        elif week_loss <= -dec(self.settings.weekly_loss_limit_pct):
            self.state.halted_reason = "weekly loss limit reached"
        elif drawdown >= dec(self.settings.max_drawdown_pct):
            self.state.halted_reason = "max drawdown reached"
