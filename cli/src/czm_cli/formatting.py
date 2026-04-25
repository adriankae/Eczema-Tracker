from __future__ import annotations

from datetime import datetime
from typing import Any

from .time_utils import format_display_date, format_due_date, format_optional_display_date, utc_isoformat


def _value(item: Any, key: str) -> Any:
    if isinstance(item, dict):
        return item[key]
    return getattr(item, key)


def _optional_value(item: Any, key: str) -> Any:
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def _kv_lines(items: list[tuple[str, str]]) -> str:
    width = max((len(label) for label, _ in items), default=0)
    return "\n".join(f"{label.ljust(width)}  {value}" for label, value in items)


def format_subject(subject: dict[str, Any]) -> str:
    return _kv_lines(
        [
            ("id", str(_value(subject, "id"))),
            ("display_name", str(_value(subject, "display_name"))),
        ]
    )


def format_subject_list(subjects: list[dict[str, Any]]) -> str:
    if not subjects:
        return "No subjects."
    lines = ["Subjects:"]
    for subject in subjects:
        lines.append(f"- {_value(subject, 'id')}: {_value(subject, 'display_name')}")
    return "\n".join(lines)


def format_location(location: dict[str, Any]) -> str:
    image = _optional_value(location, "image")
    return _kv_lines(
        [
            ("id", str(_value(location, "id"))),
            ("code", str(_value(location, "code"))),
            ("display_name", str(_value(location, "display_name"))),
            ("image", "yes" if image else "no"),
        ]
    )


def format_location_list(locations: list[dict[str, Any]]) -> str:
    if not locations:
        return "No locations."
    lines = ["Locations:"]
    for location in locations:
        image_text = ", image=yes" if _optional_value(location, "image") else ", image=no"
        lines.append(f"- {_value(location, 'id')}: {_value(location, 'code')} ({_value(location, 'display_name')}{image_text})")
    return "\n".join(lines)


def format_location_image_result(payload: dict[str, Any]) -> str:
    location = payload["location"] if isinstance(payload, dict) and "location" in payload else payload
    image = _optional_value(location, "image")
    if not image:
        return format_location(location)
    return _kv_lines(
        [
            ("id", str(_value(location, "id"))),
            ("code", str(_value(location, "code"))),
            ("display_name", str(_value(location, "display_name"))),
            ("image_mime_type", str(_value(image, "mime_type"))),
            ("image_size_bytes", str(_value(image, "size_bytes"))),
            ("image_sha256", str(_value(image, "sha256"))),
            ("image_original_filename", str(_optional_value(image, "original_filename"))),
            ("image_uploaded_at", str(_value(image, "uploaded_at"))),
            ("image_url", str(_value(image, "url"))),
        ]
    )


def format_episode(episode: dict[str, Any], timezone_name: str = "UTC") -> str:
    items = [
        ("id", str(_value(episode, "id"))),
        ("subject_id", str(_value(episode, "subject_id"))),
        ("location_id", str(_value(episode, "location_id"))),
        ("status", str(_value(episode, "status"))),
        ("current_phase_number", str(_value(episode, "current_phase_number"))),
        ("phase_started_at", format_display_date(_value(episode, "phase_started_at"), timezone_name)),
        ("phase_due_end_at", format_optional_display_date(_optional_value(episode, "phase_due_end_at"), timezone_name)),
        ("healed_at", format_optional_display_date(_optional_value(episode, "healed_at"), timezone_name)),
        ("obsolete_at", format_optional_display_date(_optional_value(episode, "obsolete_at"), timezone_name)),
    ]
    return _kv_lines(items)


def format_episode_list(episodes: list[dict[str, Any]]) -> str:
    if not episodes:
        return "No episodes."
    lines = ["Episodes:"]
    for episode in episodes:
        lines.append(
            f"- {_value(episode, 'id')}: subject {_value(episode, 'subject_id')}, location {_value(episode, 'location_id')}, phase {_value(episode, 'current_phase_number')}, {_value(episode, 'status')}"
        )
    return "\n".join(lines)


def format_application(application: dict[str, Any], timezone_name: str = "UTC") -> str:
    items = [
        ("id", str(_value(application, "id"))),
        ("episode_id", str(_value(application, "episode_id"))),
        ("applied_at", format_display_date(_value(application, "applied_at"), timezone_name)),
        ("treatment_type", str(_value(application, "treatment_type"))),
        ("treatment_name", str(_optional_value(application, "treatment_name"))),
        ("quantity_text", str(_optional_value(application, "quantity_text"))),
        ("phase_number_snapshot", str(_value(application, "phase_number_snapshot"))),
        ("is_voided", str(_value(application, "is_voided"))),
        ("voided_at", format_optional_display_date(_optional_value(application, "voided_at"), timezone_name)),
        ("deleted_at", format_optional_display_date(_optional_value(application, "deleted_at"), timezone_name)),
        ("notes", str(_optional_value(application, "notes"))),
    ]
    return _kv_lines(items)


def format_application_list(applications: list[dict[str, Any]], timezone_name: str = "UTC") -> str:
    if not applications:
        return "No applications."
    lines = ["Applications:"]
    for application in applications:
        lines.append(
            f"- {_value(application, 'id')}: {format_display_date(_value(application, 'applied_at'), timezone_name)} {_value(application, 'treatment_type')} (phase {_value(application, 'phase_number_snapshot')})"
        )
    return "\n".join(lines)


def format_due_list(items: list[dict[str, Any]], timezone_name: str = "UTC") -> str:
    if not items:
        return "No due items."
    lines = ["Due items:"]
    for item in items:
        next_due = format_due_date(_optional_value(item, "next_due_at"), _value(item, "current_phase_number"), timezone_name)
        lines.append(
            f"- episode {_value(item, 'episode_id')}: phase {_value(item, 'current_phase_number')}, due_today={_value(item, 'treatment_due_today')}, next_due={next_due}"
        )
    return "\n".join(lines)


def _score_text(score: float | None) -> str:
    if score is None:
        return "n/a"
    return f"{score * 100:.1f}%"


def _date_range_title(prefix: str, payload: dict[str, Any]) -> str:
    return f"{prefix} {_value(payload, 'from')} -> {_value(payload, 'to')}"


def _adherence_day_line(day: Any) -> str:
    return (
        f"{_value(day, 'date')}  {_value(day, 'status')}  "
        f"{_value(day, 'credited_applications')}/{_value(day, 'expected_applications')}  "
        f"episode={_value(day, 'episode_id')} phase={_value(day, 'phase_number')}"
    )


def _format_adherence_days(days: list[Any], *, empty_message: str) -> str:
    if not days:
        return empty_message
    return "\n".join(_adherence_day_line(day) for day in days)


def format_adherence_summary(payload: dict[str, Any]) -> str:
    lines = [
        _date_range_title("Adherence summary", payload),
        f"Score: {_score_text(_optional_value(payload, 'adherence_score'))}",
        f"Expected applications: {_value(payload, 'expected_applications')}",
        f"Completed applications: {_value(payload, 'completed_applications')}",
        f"Credited applications: {_value(payload, 'credited_applications')}",
        "",
        "Days:",
        f"  completed: {_value(payload, 'completed_days')}",
        f"  partial:    {_value(payload, 'partial_days')}",
        f"  missed:     {_value(payload, 'missed_days')}",
        f"  not_due:    {_value(payload, 'not_due_days')}",
        f"  future:     {_value(payload, 'future_days')}",
    ]
    return "\n".join(lines)


def format_adherence_calendar(payload: dict[str, Any], from_date: str | None = None, to_date: str | None = None) -> str:
    lines = []
    if from_date is not None and to_date is not None:
        lines.extend([f"Adherence calendar {from_date} -> {to_date}", ""])
    lines.append(_format_adherence_days(_value(payload, "days"), empty_message="No adherence days."))
    return "\n".join(lines)


def format_adherence_missed(payload: dict[str, Any], from_date: str | None = None, to_date: str | None = None) -> str:
    lines = []
    if from_date is not None and to_date is not None:
        lines.extend([f"Missed adherence days {from_date} -> {to_date}", ""])
    lines.append(_format_adherence_days(_value(payload, "days"), empty_message="No missed adherence days."))
    return "\n".join(lines)


def format_episode_adherence(payload: dict[str, Any]) -> str:
    lines = [
        f"Episode {_value(payload, 'episode_id')} adherence {_value(payload, 'from')} -> {_value(payload, 'to')}",
        "",
        format_adherence_summary(_value(payload, "summary")),
        "",
        _format_adherence_days(_value(payload, "days"), empty_message="No adherence days."),
    ]
    return "\n".join(lines)


def format_adherence_rebuild(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Adherence rebuild complete",
            "",
            f"Episodes processed: {_value(payload, 'episodes_processed')}",
            f"Rows persisted: {_value(payload, 'rows_persisted')}",
        ]
    )


def format_event_list(events: list[dict[str, Any]], timezone_name: str = "UTC") -> str:
    if not events:
        return "No events."
    lines = ["Events:"]
    for event in events:
        lines.append(f"- {_value(event, 'id')}: {format_display_date(_value(event, 'occurred_at'), timezone_name)} {_value(event, 'event_type')} ({_value(event, 'actor_type')})")
    return "\n".join(lines)


def serialize_json_payload(payload: Any) -> Any:
    if isinstance(payload, datetime):
        return utc_isoformat(payload)
    if isinstance(payload, list):
        return [serialize_json_payload(item) for item in payload]
    if isinstance(payload, dict):
        return {key: serialize_json_payload(value) for key, value in payload.items()}
    return payload
