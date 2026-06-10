from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler

from .config import Settings
from .runner import TradingBot


def start_scheduler(settings: Settings, bot: TradingBot) -> None:
    timezone = ZoneInfo(settings.timezone)
    scheduler = BlockingScheduler(timezone=timezone)

    scheduler.add_job(bot.preflight, "cron", day_of_week="mon-fri", hour=_hour(settings.schedule.preflight_time), minute=_minute(settings.schedule.preflight_time))
    scheduler.add_job(bot.refresh_universe, "cron", day_of_week="mon-fri", hour=_hour(settings.schedule.preflight_time), minute=_minute(settings.schedule.preflight_time))
    scheduler.add_job(bot.premarket_report, "cron", day_of_week="mon-fri", hour=_hour(settings.schedule.premarket_report_time), minute=_minute(settings.schedule.premarket_report_time))
    scheduler.add_job(
        bot.market_loop_once,
        "cron",
        day_of_week="mon-fri",
        hour="9-15",
        minute="*",
        second=5,
        start_date=datetime.now(tz=timezone),
    )
    scheduler.add_job(
        bot.reconcile_open_orders,
        "cron",
        day_of_week="mon-fri",
        hour="9-15",
        minute=f"*/{settings.schedule.reconcile_interval_minutes}",
        second=20,
        start_date=datetime.now(tz=timezone),
    )
    scheduler.add_job(bot.close_policy, "cron", day_of_week="mon-fri", hour=_hour(settings.schedule.close_policy_start), minute=_minute(settings.schedule.close_policy_start))
    scheduler.add_job(bot.daily_report, "cron", day_of_week="mon-fri", hour=_hour(settings.schedule.report_time), minute=_minute(settings.schedule.report_time))

    scheduler.start()


def _hour(value: str) -> int:
    return int(value.split(":", 1)[0])


def _minute(value: str) -> int:
    return int(value.split(":", 1)[1])
