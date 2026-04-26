from __future__ import annotations

from typing import Any


MAX_ROWS = 10


def _list_items(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    return value if isinstance(value, list) else []


def _cap(lines: list[str], total: int) -> list[str]:
    omitted = total - MAX_ROWS
    if omitted > 0:
        return [*lines[:MAX_ROWS], f"... {omitted} more omitted"]
    return lines


def menu_text() -> str:
    return "\n".join(
        [
            "Zema",
            "",
            "Commands:",
            "  /due",
            "  /log episode:12",
            "  /adherence 30",
            "  /subjects",
            "  /locations",
            "  /episodes",
            "  /help",
        ]
    )


def help_text() -> str:
    return "\n".join(
        [
            "Zema commands",
            "",
            "Subjects:",
            "  /subjects",
            "  /subject_create Child A",
            "",
            "Locations:",
            "  /locations",
            "  /location_create left_elbow Left elbow",
            "  /location_image_set left_elbow",
            "",
            "Episodes:",
            "  /episodes",
            "  /episode 12",
            '  /episode_create subject:"Child A" location:left_elbow',
            "",
            "Treatment:",
            "  /due",
            "  /log episode:12",
            "",
            "Adherence:",
            "  /adherence 30",
            "  /adherence_calendar episode:12 days:30",
            "  /adherence_missed episode:12 days:30",
        ]
    )


def format_subjects(payload: dict[str, Any]) -> str:
    subjects = _list_items(payload, "subjects")
    if not subjects:
        return "No subjects."
    lines = [f"{item['id']}. {item['display_name']}" for item in subjects]
    return "Subjects:\n" + "\n".join(_cap(lines, len(subjects)))


def format_subject_created(payload: dict[str, Any]) -> str:
    return f"Created subject: {payload['display_name']} (id={payload['id']})"


def format_locations(payload: dict[str, Any]) -> str:
    locations = _list_items(payload, "locations")
    if not locations:
        return "No locations."
    lines = [f"{item['id']}. {item['code']} - {item['display_name']}" for item in locations]
    return "Locations:\n" + "\n".join(_cap(lines, len(locations)))


def format_location_created(payload: dict[str, Any]) -> str:
    location = payload["location"]
    return f"Created location: {location['code']} - {location['display_name']} (id={location['id']})"


def format_episodes(payload: dict[str, Any]) -> str:
    episodes = _list_items(payload, "episodes")
    if not episodes:
        return "No episodes."
    lines = [
        f"{item['id']}. subject={item['subject_id']} location={item['location_id']} phase={item['current_phase_number']} status={item['status']}"
        for item in episodes
    ]
    return "Episodes:\n" + "\n".join(_cap(lines, len(episodes)))


def format_episode(payload: dict[str, Any]) -> str:
    episode = payload["episode"]
    return "\n".join(
        [
            f"Episode {episode['id']}",
            f"subject: {episode['subject_id']}",
            f"location: {episode['location_id']}",
            f"status: {episode['status']}",
            f"phase: {episode['current_phase_number']}",
        ]
    )


def format_episode_created(payload: dict[str, Any]) -> str:
    episode = payload["episode"]
    return f"Created episode {episode['id']} for subject={episode['subject_id']} location={episode['location_id']}."


def format_episode_action_success(action: str, payload: dict[str, Any]) -> str:
    episode = payload["episode"]
    return f"{action} episode {episode['id']}. Status: {episode['status']}."


def format_due(payload: dict[str, Any]) -> str:
    due = _list_items(payload, "due")
    if not due:
        return "No due treatments."
    lines = [
        f"{item['episode_id']}. subject={item['subject_id']} location={item['location_id']} phase={item['current_phase_number']} due={item['treatment_due_today']}"
        for item in due
    ]
    return "Due now:\n" + "\n".join(_cap(lines, len(due)))


def format_application_logged(payload: dict[str, Any]) -> str:
    application = payload["application"]
    return f"Logged application for episode {application['episode_id']}."


def format_events(payload: dict[str, Any], key: str = "events") -> str:
    events = _list_items(payload, key)
    if not events:
        return "No events."
    lines = [f"{item['id']}. {item['event_type']} at {item['occurred_at']}" for item in events]
    return "Events:\n" + "\n".join(_cap(lines, len(events)))


def format_adherence_summary(payload: dict[str, Any]) -> str:
    score = payload.get("adherence_score")
    score_text = "n/a" if score is None else f"{float(score) * 100:.0f}%"
    return "\n".join(
        [
            f"Adherence {payload.get('from')} to {payload.get('to')}:",
            f"Score: {score_text}",
            f"Expected: {payload.get('expected_applications')}",
            f"Credited: {payload.get('credited_applications')}",
            f"Missed days: {payload.get('missed_days')}",
        ]
    )


def format_adherence_days(payload: dict[str, Any], *, title: str) -> str:
    days = _list_items(payload, "days")
    if not days:
        return f"{title}: none."
    lines = [
        f"{item['date']} {item['status']} {item['credited_applications']}/{item['expected_applications']} episode={item['episode_id']} phase={item['phase_number']}"
        for item in days
    ]
    return f"{title}:\n" + "\n".join(_cap(lines, len(days)))


def format_adherence_rebuild(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Adherence rebuild complete.",
            f"Episodes processed: {payload.get('episodes_processed')}",
            f"Rows persisted: {payload.get('rows_persisted')}",
        ]
    )


def backend_error_message(message: str) -> str:
    return f"Zema request failed: {message}"
