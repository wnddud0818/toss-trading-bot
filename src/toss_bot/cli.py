from __future__ import annotations

import argparse
import logging
from datetime import date
from decimal import Decimal

from .backtest import Backtester
from .config import load_settings
from .db import BotRepository, init_db
from .models import RunMode
from .notifications import DiscordNotifier
from .reports import ReportWriter
from .runner import TradingBot
from .scheduler import start_scheduler
from .toss_client import TossApiError, TossClient


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="toss-bot")
    parser.add_argument("--config", default="config/settings.yaml")
    parser.add_argument("--log-level", default="INFO")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backtest = subparsers.add_parser("backtest")
    backtest.add_argument("--from", dest="from_date", required=True)
    backtest.add_argument("--to", dest="to_date", required=True)

    run = subparsers.add_parser("run")
    run.add_argument("--mode", choices=[RunMode.PAPER.value, RunMode.LIVE.value], default=RunMode.PAPER.value)
    run.add_argument("--once", action="store_true")

    reconcile = subparsers.add_parser("reconcile")
    reconcile.add_argument("--cancel-stale", action="store_true")

    report = subparsers.add_parser("report")
    report.add_argument("--date", required=True)

    subparsers.add_parser("doctor")
    subparsers.add_parser("status")

    halt = subparsers.add_parser("halt")
    halt.add_argument("--reason", default="manual halt")

    resume = subparsers.add_parser("resume")
    resume.add_argument("--reset-peak", action="store_true")

    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper()), format="%(asctime)s %(levelname)s %(name)s %(message)s")

    settings = load_settings(args.config)
    session_factory = init_db(settings.database_url)
    repository = BotRepository(session_factory)

    if args.command == "doctor":
        return _doctor(settings)
    if args.command == "status":
        return _status(settings, repository)
    if args.command == "halt":
        return _halt(repository, args.reason)
    if args.command == "resume":
        return _resume(repository, reset_peak=args.reset_peak)
    if args.command == "backtest":
        result = Backtester(settings).run(date.fromisoformat(args.from_date), date.fromisoformat(args.to_date))
        print(
            f"Backtest {result.start}..{result.end}: "
            f"{result.start_equity} -> {result.end_equity} "
            f"return={result.total_return:.4%} trades={result.trades} method={result.method}"
        )
        if result.warning:
            print(f"Warning: {result.warning}")
        return 0
    if args.command == "report":
        path = ReportWriter(settings, repository).write_daily_report(date.fromisoformat(args.date))
        print(path)
        return 0
    if args.command == "reconcile":
        toss_client = TossClient(settings)
        bot = TradingBot(settings, repository, toss_client, DiscordNotifier(settings))
        report = bot.reconcile_open_orders(cancel_stale=args.cancel_stale)
        print(report.summary())
        if report.errors:
            print("Errors: " + "; ".join(report.errors))
            return 1
        return 0
    if args.command == "run":
        configured_mode = settings.mode
        requested_mode = RunMode(args.mode)
        if requested_mode == RunMode.LIVE and configured_mode != RunMode.LIVE:
            raise SystemExit("Live trading requires mode: live in config/settings.yaml")
        settings.mode = requested_mode
        toss_client = TossClient(settings)
        bot = TradingBot(settings, repository, toss_client, DiscordNotifier(settings))
        if args.once:
            bot.preflight()
            bot.refresh_universe()
            bot.premarket_report()
            bot.market_loop_once()
            return 0
        start_scheduler(settings, bot)
        return 0
    return 1


def _status(settings, repository: BotRepository) -> int:
    print(f"Mode: {settings.mode.value}")
    state = repository.load_risk_state()
    if state is None:
        print("Risk state: not initialized (run the bot at least once)")
        return 0
    print(
        f"Equity: {state.current_equity} "
        f"(day start {state.start_day_equity}, week start {state.start_week_equity}, peak {state.peak_equity})"
    )
    print(f"Halted: {state.halted_reason or 'no'}")
    if settings.mode == RunMode.PAPER:
        cash = repository.get_cash(Decimal(settings.paper.initial_cash_krw))
        positions = repository.list_positions()
        print(f"Paper cash: {cash}")
        print(f"Paper positions: {len(positions)}")
        for position in positions:
            print(
                f"  {position.symbol} qty={position.quantity} entry={position.entry_price} "
                f"high={position.high_watermark} since={position.entry_date}"
            )
    else:
        print("Live positions are read from the broker at runtime; see daily reports for fills")
    audits = repository.latest_order_audits(5)
    if audits:
        print("Recent orders:")
        for audit in audits:
            print(
                f"  {audit.ts:%Y-%m-%d %H:%M} {audit.mode} {audit.side} {audit.symbol} "
                f"x{audit.quantity} status={audit.status} {audit.reason}"
            )
    return 0


def _halt(repository: BotRepository, reason: str) -> int:
    state = repository.load_risk_state()
    if state is None:
        print("No risk state found; run the bot at least once first")
        return 1
    state.halted_reason = reason
    repository.save_risk_state(state)
    print(f"Trading halted: {reason}")
    return 0


def _resume(repository: BotRepository, *, reset_peak: bool) -> int:
    state = repository.load_risk_state()
    if state is None:
        print("No risk state found; nothing to resume")
        return 1
    previous = state.halted_reason
    state.halted_reason = None
    if reset_peak:
        state.peak_equity = state.current_equity
    repository.save_risk_state(state)
    if previous == "max drawdown reached" and not reset_peak:
        print("Warning: peak equity unchanged; the max drawdown halt will trigger again (use --reset-peak after review)")
    print(f"Trading resumed (cleared: {previous or 'none'})")
    return 0


def _doctor(settings) -> int:
    missing = []
    if not settings.toss_client_id:
        missing.append("TOSSINVEST_CLIENT_ID")
    if not settings.toss_client_secret:
        missing.append("TOSSINVEST_CLIENT_SECRET")
    if settings.toss_account_seq is None:
        missing.append("TOSSINVEST_ACCOUNT_SEQ")
    if missing:
        print("Missing environment values: " + ", ".join(missing))
        return 1
    client = TossClient(settings)
    try:
        token = client.token()
        accounts = client.get_accounts()
        print(f"Toss auth ok token_prefix={token[:8]} accounts={len(accounts)}")
        calendar = client.get_kr_market_calendar()
        today = calendar.get("today", {})
        print(f"KR market calendar today={today.get('date', 'unknown')}")
        commissions = client.get_commissions()
        kr_commissions = [item for item in commissions if item.get("marketCountry") == "KR"]
        if kr_commissions:
            print(f"KR commission configured: {kr_commissions[0].get('commissionRate')}")
    except TossApiError as exc:
        print(f"Toss check failed: {exc}")
        return 1
    finally:
        client.close()
    if settings.discord_webhook_url:
        print("Discord webhook configured")
    else:
        print("Discord webhook not configured")
    if settings.mode == RunMode.LIVE and not settings.enable_live_trading:
        print("Live config is set but ENABLE_LIVE_TRADING is false")
        return 1
    print("Doctor ok")
    return 0
