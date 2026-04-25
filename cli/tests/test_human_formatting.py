from __future__ import annotations

from datetime import datetime, timezone

from czm_cli.formatting import format_application, format_due_list, format_episode, format_event_list, serialize_json_payload


BERLIN = "Europe/Berlin"
UTC = timezone.utc


def test_phase1_due_uses_am_pm_label():
    morning_due = [
        {
            "episode_id": 1,
            "current_phase_number": 1,
            "treatment_due_today": True,
            "next_due_at": datetime(2026, 4, 15, 6, 0, tzinfo=UTC),
        }
    ]
    evening_due = [
        {
            "episode_id": 2,
            "current_phase_number": 1,
            "treatment_due_today": True,
            "next_due_at": datetime(2026, 4, 15, 16, 0, tzinfo=UTC),
        }
    ]
    morning_text = format_due_list(morning_due, BERLIN)
    evening_text = format_due_list(evening_due, BERLIN)
    assert "next_due=AM, 15.04.26" in morning_text
    assert "next_due=PM, 15.04.26" in evening_text


def test_phase2_due_uses_date_only():
    text = format_due_list(
        [
            {
                "episode_id": 1,
                "current_phase_number": 2,
                "treatment_due_today": False,
                "next_due_at": datetime(2026, 4, 15, 16, 0, tzinfo=UTC),
            }
        ],
        BERLIN,
    )
    assert "next_due=15.04.26" in text
    assert "AM" not in text
    assert "PM" not in text


def test_lifecycle_and_event_fields_render_as_dates():
    episode_text = format_episode(
        {
            "id": 1,
            "subject_id": 1,
            "location_id": 1,
            "status": "active_flare",
            "current_phase_number": 1,
            "phase_started_at": datetime(2026, 4, 15, 23, 30, tzinfo=UTC),
            "phase_due_end_at": datetime(2026, 4, 15, 23, 30, tzinfo=UTC),
            "healed_at": datetime(2026, 4, 15, 23, 30, tzinfo=UTC),
            "obsolete_at": datetime(2026, 4, 15, 23, 30, tzinfo=UTC),
        },
        BERLIN,
    )
    for field in ["phase_started_at", "phase_due_end_at", "healed_at", "obsolete_at"]:
        line = next(line for line in episode_text.splitlines() if line.startswith(field))
        assert line.endswith("16.04.26")
        assert "T" not in line
        assert "Z" not in line

    application_text = format_application(
        {
            "id": 1,
            "episode_id": 1,
            "applied_at": datetime(2026, 4, 15, 23, 30, tzinfo=UTC),
            "treatment_type": "steroid",
            "treatment_name": "Hydrocortisone 1%",
            "quantity_text": "thin layer",
            "phase_number_snapshot": 2,
            "is_voided": False,
            "voided_at": datetime(2026, 4, 15, 23, 30, tzinfo=UTC),
            "deleted_at": datetime(2026, 4, 15, 23, 30, tzinfo=UTC),
            "notes": "evening dose",
        },
        BERLIN,
    )
    for field in ["applied_at", "voided_at", "deleted_at"]:
        line = next(line for line in application_text.splitlines() if line.startswith(field))
        assert line.endswith("16.04.26")
        assert "T" not in line
        assert "Z" not in line

    event_text = format_event_list(
        [
            {
                "id": 1,
                "event_uuid": "uuid",
                "episode_id": 1,
                "event_type": "episode_created",
                "actor_type": "agent",
                "actor_id": None,
                "occurred_at": datetime(2026, 4, 15, 23, 30, tzinfo=UTC),
                "payload": {},
            }
        ],
        BERLIN,
    )
    assert "16.04.26" in event_text
    assert "2026-04-15T23:30:00" not in event_text


def test_json_serialization_preserves_utc_iso():
    payload = {
        "episode": {
            "phase_started_at": datetime(2026, 4, 15, 23, 30, tzinfo=UTC),
            "nested": [datetime(2026, 4, 15, 23, 30, tzinfo=UTC)],
        }
    }
    serialized = serialize_json_payload(payload)
    assert serialized == {
        "episode": {
            "phase_started_at": "2026-04-15T23:30:00Z",
            "nested": ["2026-04-15T23:30:00Z"],
        }
    }
