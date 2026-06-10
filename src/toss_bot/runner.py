from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from .brokers import LiveBroker, PaperBroker
from .config import Settings
from .db import BotRepository
from .execution import ExecutionPlanner
from .market_calendar import KrMarketSession, parse_kr_market_session
from .market_filter import MarketFilter
from .models import Candle, OrderSide, RunMode, Signal
from .notifications import DiscordNotifier
from .order_reconcile import OrderReconciler, ReconcileReport
from .reports import ReportWriter
from .risk import RiskManager, RiskState
from .strategy import HybridMomentumStrategy
from .toss_client import TossClient
from .universe import UniverseBuilder
from .utils import dec, now_kst, parse_toss_candle

logger = logging.getLogger(__name__)


class TradingBot:
    def __init__(
        self,
        settings: Settings,
        repository: BotRepository,
        toss_client: TossClient,
        notifier: DiscordNotifier,
    ):
        self.settings = settings
        self.repository = repository
        self.toss_client = toss_client
        self.notifier = notifier
        self.universe_builder = UniverseBuilder(settings.universe, repository, toss_client)
        self.strategy = HybridMomentumStrategy(settings.strategy)
        self.execution = ExecutionPlanner(settings.execution, settings.risk, toss_client)
        self.order_reconciler = OrderReconciler(settings.execution, toss_client)
        self.market_filter = MarketFilter()
        self.report_writer = ReportWriter(settings, repository)
        self.broker = self._make_broker()
        self._session_cache_date = None
        self._session_cache: KrMarketSession | None = None
        equity = self.broker.portfolio_value({})
        self.risk = RiskManager(
            settings.risk,
            RiskState(
                start_day_equity=equity,
                start_week_equity=equity,
                peak_equity=equity,
                current_equity=equity,
            ),
            {position.symbol: position for position in self.broker.positions()},
        )

    def preflight(self) -> None:
        self.toss_client.get_accounts()
        session = self._market_session()
        self.notifier.send(f"[toss-bot] preflight ok mode={self.settings.mode.value} kr_session={session.label()}")

    def refresh_universe(self, as_of: date | None = None) -> None:
        as_of = as_of or now_kst().date()
        candidates = self.universe_builder.refresh(as_of)
        self.notifier.send(f"[toss-bot] universe refreshed: {len(candidates)} candidates")

    def premarket_report(self) -> None:
        ranked = self._ranked_candidates()
        preview = ", ".join(f"{item.symbol}:{item.score:.3f}" for item in ranked[:10])
        self.notifier.send(f"[toss-bot] premarket top candidates: {preview or 'none'}")

    def market_loop_once(self) -> None:
        current_time = now_kst().strftime("%H:%M")
        if current_time > self.settings.schedule.market_loop_end:
            logger.info("Market loop skipped after configured end time")
            return
        session = self._market_session()
        if not session.orders_open(now_kst()):
            logger.info("Market loop skipped outside regular KR session: %s", session.label())
            return
        today = now_kst().date()
        market_ok = self.market_filter.risk_on(today)
        positions = {position.symbol: position for position in self.broker.positions()}
        latest_prices = self._latest_prices(list(positions))
        equity = self.broker.portfolio_value(latest_prices)
        self.risk.positions = positions
        self.risk.update_equity(equity)
        self.repository.record_equity(now_kst(), equity)

        self._process_exits(positions, today, market_ok)
        if not market_ok:
            logger.info("Market filter is risk-off; skipping entries")
            return
        if not session.new_entries_allowed(now_kst()):
            logger.info("New entries skipped near closing auction: %s", session.label())
            return
        self._process_entries()

    def close_policy(self) -> None:
        for position in self.broker.positions():
            candles = self._candles(position.symbol, "1m", 30)
            if not candles:
                continue
            latest = candles[-1]
            self._update_high_watermark(position.symbol, latest.high)
            signal = self.strategy.exit_signal(position, candles, now_kst().date(), market_filter_ok=False)
            if signal is None:
                continue
            self._place_signal(signal, urgent=True)

    def reconcile_open_orders(self, *, cancel_stale: bool | None = None) -> ReconcileReport:
        report = self.order_reconciler.reconcile(cancel_stale=cancel_stale)
        self.notifier.send(f"[toss-bot] order reconcile {report.summary()}")
        if report.errors:
            logger.warning("Order reconcile errors: %s", report.errors)
        return report

    def daily_report(self) -> None:
        path = self.report_writer.write_daily_report(now_kst().date())
        self.notifier.send(f"[toss-bot] daily report written: {path}")

    def _process_exits(self, positions: dict[str, object], today: date, market_ok: bool) -> None:
        for position in list(positions.values()):
            candles = self._candles(position.symbol, "1m", 80)
            if candles:
                self._update_high_watermark(position.symbol, max(candle.high for candle in candles))
            signal = self.strategy.exit_signal(position, candles, today, market_filter_ok=market_ok)
            if signal is None:
                continue
            self._place_signal(signal, urgent=True)

    def _process_entries(self) -> None:
        if now_kst().strftime("%H:%M") >= self.settings.strategy.new_entries_cutoff:
            logger.info("New entries are disabled after cutoff")
            return
        cash = self.broker.cash()
        for candidate in self._ranked_candidates()[: self.settings.strategy.max_positions]:
            can_enter, reason = self.risk.can_enter(candidate.symbol, cash, self.settings.strategy.max_positions)
            if not can_enter:
                logger.info("Skip entry %s: %s", candidate.symbol, reason)
                continue
            budget = self.risk.position_budget(cash, candidate.volatility, dec(self.settings.strategy.stop_loss_pct))
            if budget <= 0:
                return
            daily = self._candles(candidate.symbol, "1d", 130)
            intraday = self._candles(candidate.symbol, "1m", 80)
            signal = self.strategy.entry_signal(candidate, daily, intraday, budget)
            if signal is None:
                continue
            result = self._place_signal(signal, urgent=False)
            if result is None:
                continue
            cash = self.broker.cash()
            self.notifier.send(f"[toss-bot] entry {signal.symbol}: {result.status} {signal.reason}")

    def _place_signal(self, signal: Signal, *, urgent: bool):
        plan = self.execution.plan(signal, urgent=urgent or signal.side == OrderSide.SELL)
        if not plan.accepted or plan.order is None:
            logger.info("Execution rejected %s %s: %s", signal.side, signal.symbol, plan.reason)
            if signal.side == OrderSide.BUY:
                return None
            self.notifier.send(f"[toss-bot] exit rejected {signal.symbol}: {plan.reason}")
            return None
        result = self.broker.place_order(plan.order, reason=signal.reason)
        self.repository.record_order(now_kst(), self.settings.mode.value, plan.order, result, reason=signal.reason)
        return result

    def _update_high_watermark(self, symbol: str, high_watermark: Decimal) -> None:
        updater = getattr(self.broker, "update_high_watermark", None)
        if updater is not None:
            updater(symbol, high_watermark)

    def _ranked_candidates(self):
        universe = self.repository.load_latest_universe()
        daily = {candidate.symbol: self._candles(candidate.symbol, "1d", 130) for candidate in universe}
        return self.strategy.rank_candidates(universe, daily)

    def _candles(self, symbol: str, interval: str, count: int) -> list[Candle]:
        result = self.toss_client.get_candles(symbol, interval, count)
        candles = result.get("candles", result if isinstance(result, list) else [])
        return [parse_toss_candle(item) for item in candles]

    def _latest_prices(self, symbols: list[str]) -> dict[str, Decimal]:
        if not symbols:
            return {}
        prices = self.toss_client.get_prices(symbols)
        items = prices.get("prices", prices if isinstance(prices, list) else [])
        return {item["symbol"]: dec(item["lastPrice"]) for item in items}

    def _market_session(self) -> KrMarketSession:
        today = now_kst().date()
        if self._session_cache_date == today and self._session_cache is not None:
            return self._session_cache
        calendar = self.toss_client.get_kr_market_calendar()
        session = parse_kr_market_session(calendar)
        self._session_cache_date = today
        self._session_cache = session
        return session

    def _make_broker(self):
        if self.settings.mode == RunMode.PAPER:
            return PaperBroker(self.settings, self.repository)
        return LiveBroker(self.settings, self.toss_client)
