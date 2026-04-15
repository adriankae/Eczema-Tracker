from __future__ import annotations

from datetime import date, datetime, time, timezone, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings


def deployment_tz() -> ZoneInfo:
    return ZoneInfo(settings.deployment_timezone)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(deployment_tz())


def local_date(dt: datetime) -> date:
    return to_local(dt).date()


def local_midnight(dt_or_date: datetime | date) -> datetime:
    if isinstance(dt_or_date, datetime):
        target_date = to_local(dt_or_date).date()
    else:
        target_date = dt_or_date
    return datetime.combine(target_date, time.min, tzinfo=deployment_tz()).astimezone(timezone.utc)


def add_calendar_days(dt: datetime, days: int) -> datetime:
    return (to_local(dt) + timedelta(days=days)).astimezone(timezone.utc)
