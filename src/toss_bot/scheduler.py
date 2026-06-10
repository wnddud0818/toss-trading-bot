from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler

from .config import Settings
from .models import MarketCountry
from .runner import TradingBot

# 정규장 커버 범위(KST). 실제 주문 가능 여부는 루프가 장 캘린더로 다시 확인하므로
# 여기서는 세션을 넉넉히 덮는 코스 필터만 담당한다.
KR_LOOP_HOURS = "9-15"
# 미국 정규장은 KST 22:30(서머타임) 또는 23:30에 시작해 다음날 05:00/06:00에 끝난다.
US_LOOP_HOURS = "0-6,22-23"


def start_scheduler(settings: Settings, bot: TradingBot) -> None:
    timezone = ZoneInfo(settings.timezone)
    scheduler = BlockingScheduler(timezone=timezone)
    started_at = datetime.now(tz=timezone)
    enabled = set(settings.enabled_markets())

    scheduler.add_job(
        bot.preflight,
        "cron",
        day_of_week="mon-fri",
        hour=_hour(settings.schedule.preflight_time),
        minute=_minute(settings.schedule.preflight_time),
    )

    if MarketCountry.KR in enabled:
        scheduler.add_job(
            bot.refresh_universe,
            "cron",
            args=[MarketCountry.KR],
            day_of_week="mon-fri",
            hour=_hour(settings.schedule.preflight_time),
            minute=_minute(settings.schedule.preflight_time),
        )
        scheduler.add_job(
            bot.premarket_report,
            "cron",
            args=[MarketCountry.KR],
            day_of_week="mon-fri",
            hour=_hour(settings.schedule.premarket_report_time),
            minute=_minute(settings.schedule.premarket_report_time),
        )
        scheduler.add_job(
            bot.market_loop_once,
            "cron",
            args=[MarketCountry.KR],
            day_of_week="mon-fri",
            hour=KR_LOOP_HOURS,
            minute="*",
            second=5,
            start_date=started_at,
        )
        scheduler.add_job(
            bot.reconcile_open_orders,
            "cron",
            day_of_week="mon-fri",
            hour=KR_LOOP_HOURS,
            minute=f"*/{settings.schedule.reconcile_interval_minutes}",
            second=20,
            start_date=started_at,
        )

    if MarketCountry.US in enabled:
        scheduler.add_job(
            bot.refresh_universe,
            "cron",
            args=[MarketCountry.US],
            day_of_week="mon-fri",
            hour=_hour(settings.schedule.us_universe_refresh_time),
            minute=_minute(settings.schedule.us_universe_refresh_time),
        )
        # 미국 세션은 KST 화-토 새벽까지 이어지므로 토요일 새벽도 포함한다.
        scheduler.add_job(
            bot.market_loop_once,
            "cron",
            args=[MarketCountry.US],
            day_of_week="mon-sat",
            hour=US_LOOP_HOURS,
            minute="*",
            second=5,
            start_date=started_at,
        )
        scheduler.add_job(
            bot.reconcile_open_orders,
            "cron",
            day_of_week="mon-sat",
            hour=US_LOOP_HOURS,
            minute=f"*/{settings.schedule.reconcile_interval_minutes}",
            second=20,
            start_date=started_at,
        )

    report_days = "mon-sat" if MarketCountry.US in enabled else "mon-fri"
    scheduler.add_job(
        bot.daily_report,
        "cron",
        day_of_week=report_days,
        hour=_hour(settings.schedule.report_time),
        minute=_minute(settings.schedule.report_time),
    )

    scheduler.start()


def _hour(value: str) -> int:
    return int(value.split(":", 1)[0])


def _minute(value: str) -> int:
    return int(value.split(":", 1)[1])
