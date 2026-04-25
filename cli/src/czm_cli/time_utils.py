from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo


def get_zone(timezone_name: str) -> ZoneInfo:
    return ZoneInfo(timezone_name)


def parse_local_datetime(value: str, timezone_name: str) -> datetime:
    normalized = value.strip()
    candidate = normalized.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        parsed_date = date.fromisoformat(normalized)
        parsed = datetime.combine(parsed_date, time.min)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=get_zone(timezone_name))
    return parsed.astimezone(timezone.utc)


def parse_local_date(value: str) -> date:
    return date.fromisoformat(value.strip())


def local_today(timezone_name: str) -> date:
    return datetime.now(get_zone(timezone_name)).date()


def utc_isoformat(dt: datetime) -> str:
    aware = dt.astimezone(timezone.utc)
    return aware.isoformat().replace("+00:00", "Z")


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def format_display_date(value: datetime, timezone_name: str) -> str:
    local = _ensure_aware(value).astimezone(get_zone(timezone_name))
    return local.strftime("%d.%m.%y")


def format_optional_display_date(value: datetime | None, timezone_name: str) -> str:
    if value is None:
        return "None"
    return format_display_date(value, timezone_name)


def format_due_date(value: datetime | None, phase_number: int, timezone_name: str) -> str:
    if value is None:
        return "none"
    local = _ensure_aware(value).astimezone(get_zone(timezone_name))
    date_text = local.strftime("%d.%m.%y")
    if phase_number == 1:
        # Phase 1 is twice daily; use the local clock split to label the slot.
        return f"{'AM' if local.hour < 12 else 'PM'}, {date_text}"
    return date_text
