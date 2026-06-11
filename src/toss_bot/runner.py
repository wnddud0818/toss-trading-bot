from __future__ import annotations

import logging
import time
from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

from .brokers import LiveBroker, PaperBroker
from .config import Settings
from .db import BotRepository
from .execution import ExecutionPlanner
from .fx import FxRateProvider
from .market_calendar import MarketSession, parse_market_session
from .market_filter import MarketFilter
from .markets import currency_for, market_for_symbol
from .models import Candle, MarketCountry, OrderSide, Position, RunMode, Signal
from .notifications import DiscordNotifier
from .order_reconcile import OrderReconciler, ReconcileReport
from .reports import ReportWriter
from .risk import RiskManager, RiskState
from .strategy import HybridMomentumStrategy
from .toss_client import TossClient
from .universe import UniverseBuilder
from .utils import dec, extract_items, now_kst, parse_toss_candle

logger = logging.getLogger(__name__)

SESSION_CACHE_TTL_SECONDS = 1800
# 유니버스 전 종목 일봉 재조회는 비싸므로 랭킹을 잠시 캐시한다.
RANK_CACHE_TTL_SECONDS = 300
# 정규장 전체(KR 381분, US 390분)를 덮어 세션 시가·VWAP·박스 계산이 온전하도록 한다.
INTRADAY_CANDLE_COUNT = 400
US_EASTERN = ZoneInfo("America/New_York")


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
        self.fx = FxRateProvider(toss_client, settings.fx)
        self.profiles = {market: settings.market_profile(market) for market in settings.enabled_markets()}
        if not self.profiles:
            raise RuntimeError("no enabled markets in settings")
        self.universe_builders = {
            market: UniverseBuilder(profile.universe, repository, toss_client, market)
            for market, profile in self.profiles.items()
        }
        self.strategies = {
            market: HybridMomentumStrategy(profile.strategy, profile.costs, market)
            for market, profile in self.profiles.items()
        }
        self.planners = {
            market: ExecutionPlanner(profile.execution, profile.costs, toss_client, market)
            for market, profile in self.profiles.items()
        }
        first_profile = next(iter(self.profiles.values()))
        self.order_reconciler = OrderReconciler(
            first_profile.execution,
            toss_client,
            allowed_currencies={str(currency_for(market)) for market in self.profiles},
        )
        self.market_filter = MarketFilter(toss_client)
        self.report_writer = ReportWriter(settings, repository)
        self.broker = self._make_broker()
        self._session_cache: dict[tuple[MarketCountry, date], tuple[float, MarketSession]] = {}
        self._rank_cache: dict[MarketCountry, tuple[float, list]] = {}
        equity = self.broker.portfolio_value({})
        today = now_kst().date()
        iso = today.isocalendar()
        risk_state = repository.load_risk_state() or RiskState(
            start_day_equity=equity,
            start_week_equity=equity,
            peak_equity=equity,
            current_equity=equity,
            trading_day=today,
            iso_year=iso.year,
            iso_week=iso.week,
        )
        self.risk = RiskManager(
            settings.risk,
            risk_state,
            {position.symbol: position for position in self.broker.positions()},
        )
        self.risk.update_equity(equity, today)
        self.repository.save_risk_state(self.risk.state)
        self._last_halt_reason = self.risk.state.halted_reason

    def preflight(self) -> None:
        self.toss_client.get_accounts()
        labels = ", ".join(f"{market}={self._market_session(market).label()}" for market in self.profiles)
        self.notifier.send(f"[toss-bot] preflight ok mode={self.settings.mode.value} sessions: {labels}")

    def refresh_universe(self, market: MarketCountry | str = MarketCountry.KR, as_of: date | None = None) -> None:
        market = MarketCountry(market)
        if market not in self.universe_builders:
            logger.info("Universe refresh skipped: market %s disabled", market)
            return
        as_of = as_of or _market_date(market, now_kst())
        candidates = self.universe_builders[market].refresh(as_of)
        self._rank_cache.pop(market, None)
        self.notifier.send(f"[toss-bot] {market} universe refreshed: {len(candidates)} candidates")

    def premarket_report(self, market: MarketCountry | str = MarketCountry.KR) -> None:
        market = MarketCountry(market)
        ranked = self._ranked_candidates(market)
        preview = ", ".join(f"{item.symbol}:{item.score:.3f}" for item in ranked[:10])
        self.notifier.send(f"[toss-bot] {market} premarket top candidates: {preview or 'none'}")

    def market_loop_once(self, market: MarketCountry | str = MarketCountry.KR) -> None:
        market = MarketCountry(market)
        if market not in self.profiles:
            logger.info("Market loop skipped: market %s disabled", market)
            return
        session = self._market_session(market)
        now = now_kst()
        if not session.orders_open(now):
            logger.info("Market loop skipped outside %s regular session: %s", market, session.label())
            return
        today = _market_date(market, now)
        market_signal = self.market_filter.risk_on(market, today)
        market_ok = market_signal is True
        all_positions = self.broker.positions()
        market_positions = {
            position.symbol: position
            for position in all_positions
            if market_for_symbol(position.symbol) == market
        }
        latest_prices = self._latest_prices([position.symbol for position in all_positions])
        equity = self.broker.portfolio_value(latest_prices)
        # CLI의 halt/resume이 DB에만 반영되므로 루프마다 저장된 상태를 권위로 삼는다.
        stored_state = self.repository.load_risk_state()
        if stored_state is not None:
            self.risk.state = stored_state
        self.risk.positions = {position.symbol: position for position in all_positions}
        self.risk.update_equity(equity, today)
        self.repository.save_risk_state(self.risk.state)
        self.repository.record_equity(now, equity)
        self._notify_halt_change()

        self._process_exits(market, market_positions, today, market_ok if market_signal is not None else True)
        if market_signal is None:
            logger.info("%s market filter data unavailable; skipping entries without risk-off exits", market)
            return
        if not market_ok:
            logger.info("%s market filter is risk-off; skipping entries", market)
            return
        if not session.new_entries_allowed(now):
            logger.info("%s new entries skipped near session close: %s", market, session.label())
            return
        self._process_entries(market)

    def reconcile_open_orders(self, *, cancel_stale: bool | None = None) -> ReconcileReport:
        report = self.order_reconciler.reconcile(cancel_stale=cancel_stale)
        self.notifier.send(f"[toss-bot] order reconcile {report.summary()}")
        if report.errors:
            logger.warning("Order reconcile errors: %s", report.errors)
        return report

    def daily_report(self) -> None:
        path = self.report_writer.write_daily_report(now_kst().date())
        self.notifier.send(f"[toss-bot] daily report written: {path}")

    def _process_exits(
        self,
        market: MarketCountry,
        positions: dict[str, object],
        today: date,
        market_ok: bool,
    ) -> None:
        strategy = self.strategies[market]
        for position in list(positions.values()):
            try:
                candles = self._candles(position.symbol, "1m", INTRADAY_CANDLE_COUNT)
                if candles:
                    session_high = max(candle.high for candle in candles)
                    self._update_high_watermark(position.symbol, session_high)
                    if session_high > position.high_watermark:
                        # 저장만 하고 stale 포지션으로 판정하면 트레일링 스탑이 한 루프 늦게 조여진다.
                        position = Position(
                            symbol=position.symbol,
                            quantity=position.quantity,
                            entry_price=position.entry_price,
                            entry_date=position.entry_date,
                            high_watermark=session_high,
                        )
                signal = strategy.exit_signal(position, candles, today, market_filter_ok=market_ok)
                if signal is None:
                    continue
                self._place_signal(market, signal, urgent=True)
            except Exception:
                # 한 종목 처리 실패가 나머지 포지션의 손절까지 막으면 안 된다.
                logger.exception("Exit processing failed for %s", position.symbol)

    def _process_entries(self, market: MarketCountry) -> None:
        profile = self.profiles[market]
        currency = currency_for(market)
        today = _market_date(market, now_kst())
        cash_local = self.broker.cash(currency)
        cash_krw = self.fx.to_krw(cash_local, currency)
        open_count = sum(
            1 for position in self.broker.positions() if market_for_symbol(position.symbol) == market
        )
        # 상위 후보 다수는 당일 돌파 조건을 못 채우므로 max_positions보다 넓게 본다.
        # 포지션 수 한도는 can_enter가 매 진입마다 다시 확인한다.
        candidate_pool = self._ranked_candidates(market)[: profile.strategy.max_positions * 3]
        for candidate in candidate_pool:
            if open_count >= profile.strategy.max_positions:
                break
            try:
                last_sell = self.repository.last_sell_date(self.settings.mode.value, candidate.symbol)
                if (
                    last_sell is not None
                    and (today - last_sell).days < profile.strategy.reentry_cooldown_days
                ):
                    logger.info("Skip entry %s: re-entry cooldown active", candidate.symbol)
                    continue
                can_enter, reason = self.risk.can_enter(
                    candidate.symbol,
                    cash_krw,
                    profile.strategy.max_positions,
                    open_positions=open_count,
                )
                if not can_enter:
                    logger.info("Skip entry %s: %s", candidate.symbol, reason)
                    continue
                budget_krw = self.risk.position_budget(
                    cash_krw, candidate.volatility, dec(profile.strategy.stop_loss_pct)
                )
                budget = self.fx.from_krw(budget_krw, currency)
                if budget < Decimal(profile.costs.min_order_amount):
                    logger.info("Skip entry %s: budget below minimum order amount", candidate.symbol)
                    continue
                daily = self._candles(candidate.symbol, "1d", 130)
                intraday = self._candles(candidate.symbol, "1m", INTRADAY_CANDLE_COUNT)
                signal = self.strategies[market].entry_signal(candidate, daily, intraday, budget)
                if signal is None:
                    continue
                result = self._place_signal(market, signal, urgent=False)
                if result is None:
                    continue
                open_count += 1
                cash_local = self.broker.cash(currency)
                cash_krw = self.fx.to_krw(cash_local, currency)
                self.notifier.send(f"[toss-bot] {market} entry {signal.symbol}: {result.status} {signal.reason}")
            except Exception:
                logger.exception("Entry processing failed for %s", candidate.symbol)

    def _place_signal(self, market: MarketCountry, signal: Signal, *, urgent: bool):
        plan = self.planners[market].plan(signal, urgent=urgent or signal.side == OrderSide.SELL)
        if not plan.accepted or plan.order is None:
            logger.info("Execution rejected %s %s: %s", signal.side, signal.symbol, plan.reason)
            if signal.side == OrderSide.SELL:
                self.notifier.send(f"[toss-bot] exit rejected {signal.symbol}: {plan.reason}")
            return None
        try:
            result = self.broker.place_order(plan.order, reason=signal.reason)
        except Exception as exc:
            logger.exception("Order placement failed %s %s", signal.side, signal.symbol)
            if signal.side == OrderSide.SELL:
                self.notifier.send(f"[toss-bot] exit order failed {signal.symbol}: {exc}")
            return None
        self.repository.record_order(now_kst(), self.settings.mode.value, plan.order, result, reason=signal.reason)
        return result

    def _notify_halt_change(self) -> None:
        reason = self.risk.state.halted_reason
        if reason == self._last_halt_reason:
            return
        if reason:
            self.notifier.send(f"[toss-bot] trading halted: {reason}")
        else:
            self.notifier.send("[toss-bot] trading halt cleared")
        self._last_halt_reason = reason

    def _update_high_watermark(self, symbol: str, high_watermark: Decimal) -> None:
        updater = getattr(self.broker, "update_high_watermark", None)
        if updater is not None:
            updater(symbol, high_watermark)

    def _ranked_candidates(self, market: MarketCountry):
        # 유니버스 전 종목의 일봉을 매 분 다시 받으면 API 한도와 루프 시간을 잡아먹는다.
        cached = self._rank_cache.get(market)
        if cached is not None and time.time() - cached[0] < RANK_CACHE_TTL_SECONDS:
            return cached[1]
        universe = self.repository.load_latest_universe(market)
        daily = {candidate.symbol: self._candles(candidate.symbol, "1d", 130) for candidate in universe}
        ranked = self.strategies[market].rank_candidates(universe, daily)
        self._rank_cache[market] = (time.time(), ranked)
        return ranked

    def _candles(self, symbol: str, interval: str, count: int) -> list[Candle]:
        result = self.toss_client.get_candles(symbol, interval, count)
        return [parse_toss_candle(item) for item in extract_items(result, "candles")]

    def _latest_prices(self, symbols: list[str]) -> dict[str, Decimal]:
        if not symbols:
            return {}
        prices = self.toss_client.get_prices(symbols)
        return {item["symbol"]: dec(item["lastPrice"]) for item in extract_items(prices, "prices")}

    def _market_session(self, market: MarketCountry) -> MarketSession:
        # 미국 세션은 KST 자정을 넘기므로 날짜 기준 캐시 대신 TTL 캐시를 쓴다.
        now = now_kst()
        calendar_date = _market_date(market, now)
        cache_key = (market, calendar_date)
        cached = self._session_cache.get(cache_key)
        if cached is not None and time.time() - cached[0] < SESSION_CACHE_TTL_SECONDS:
            return cached[1]
        payload = self.toss_client.get_market_calendar(str(market), calendar_date.isoformat())
        session = parse_market_session(payload, market, self.profiles[market].strategy.entry_cutoff_minutes, now)
        self._session_cache[cache_key] = (time.time(), session)
        return session

    def _make_broker(self):
        if self.settings.mode == RunMode.PAPER:
            return PaperBroker(self.settings, self.repository, self.fx)
        return LiveBroker(self.settings, self.toss_client, self.repository, self.fx)


def _market_date(market: MarketCountry, now) -> date:
    if market == MarketCountry.US:
        return now.astimezone(US_EASTERN).date()
    return now.date()
