from __future__ import annotations

from datetime import datetime, timezone


def _create_subject_location(client, headers):
    subject = client.post("/subjects", headers=headers, json={"display_name": "Child"}).json()
    location = client.post("/locations", headers=headers, json={"code": "left_elbow", "display_name": "Left elbow"}).json()
    return subject["id"], location["location"]["id"]


def _create_episode(client, headers, *, location_code="left_elbow", location_name="Left elbow"):
    subject = client.post("/subjects", headers=headers, json={"display_name": f"Child {location_code}"}).json()
    location = client.post("/locations", headers=headers, json={"code": location_code, "display_name": location_name}).json()
    return client.post(
        "/episodes",
        headers=headers,
        json={"subject_id": subject["id"], "location_id": location["location"]["id"]},
    ).json()["episode"]


def test_episode_lifecycle(client, auth_headers):
    subject_id, location_id = _create_subject_location(client, auth_headers)
    created = client.post("/episodes", headers=auth_headers, json={"subject_id": subject_id, "location_id": location_id})
    assert created.status_code == 201
    episode = created.json()["episode"]
    assert episode["current_phase_number"] == 1

    duplicate = client.post("/episodes", headers=auth_headers, json={"subject_id": subject_id, "location_id": location_id})
    assert duplicate.status_code == 409

    heal = client.post(f"/episodes/{episode['id']}/heal", headers=auth_headers, json={"healed_at": "2026-04-05T18:00:00Z"})
    assert heal.status_code == 200
    healed = heal.json()["episode"]
    assert healed["current_phase_number"] == 2
    assert healed["status"] == "in_taper"

    relapse = client.post(f"/episodes/{episode['id']}/relapse", headers=auth_headers, json={"reported_at": "2026-04-06T18:00:00Z", "reason": "symptoms_returned"})
    assert relapse.status_code == 200
    relapsed = relapse.json()["episode"]
    assert relapsed["current_phase_number"] == 1
    assert relapsed["status"] == "active_flare"
    assert relapsed["healed_at"] is None

    heal_again = client.post(f"/episodes/{episode['id']}/heal", headers=auth_headers, json={"healed_at": "2026-04-07T18:00:00Z"})
    assert heal_again.status_code == 200
    healed_again = heal_again.json()["episode"]
    assert healed_again["current_phase_number"] == 2
    assert healed_again["status"] == "in_taper"
    assert healed_again["healed_at"] is not None


def test_auto_advance_and_obsolete(client, auth_headers):
    subject_id, location_id = _create_subject_location(client, auth_headers)
    episode = client.post("/episodes", headers=auth_headers, json={"subject_id": subject_id, "location_id": location_id}).json()["episode"]
    client.post(f"/episodes/{episode['id']}/heal", headers=auth_headers, json={"healed_at": "2026-01-01T00:00:00Z"})

    from app.core.database import SessionLocal
    from app.core.time import utc_now
    from app.services import auto_advance_due_episodes
    from app.models import EczemaEpisode

    db = SessionLocal()
    try:
        ep = db.get(EczemaEpisode, episode["id"])
        ep.phase_started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        ep.phase_due_end_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
        db.commit()
        auto_advance_due_episodes(db, datetime(2026, 3, 15, tzinfo=timezone.utc))
        db.refresh(ep)
        assert ep.status == "obsolete"
        assert ep.current_phase_number == 7
    finally:
        db.close()


def test_phase_one_due_uses_morning_and_evening_slots(client, auth_headers, monkeypatch):
    import app.services as services

    episode = _create_episode(client, auth_headers, location_code="slot_elbow", location_name="Slot elbow")
    episode_id = episode["id"]

    monkeypatch.setattr(services, "utc_now", lambda: datetime(2026, 4, 6, 9, tzinfo=timezone.utc))
    morning_due = client.get("/episodes/due", headers=auth_headers)
    assert morning_due.status_code == 200
    assert morning_due.json()["due"] == [
        {
            "episode_id": episode_id,
            "subject_id": episode["subject_id"],
            "location_id": episode["location_id"],
            "current_phase_number": 1,
            "treatment_due_today": True,
            "next_due_at": "2026-04-06T00:00:00Z",
            "last_application_at": None,
            "due_slot": "morning",
            "missed_slots_today": [],
            "applications_completed_today": 0,
            "applications_expected_today": 2,
        }
    ]

    logged_morning = client.post(
        "/applications",
        headers=auth_headers,
        json={"episode_id": episode_id, "applied_at": "2026-04-06T09:30:00Z"},
    )
    assert logged_morning.status_code == 201
    assert client.get("/episodes/due", headers=auth_headers).json()["due"] == []

    monkeypatch.setattr(services, "utc_now", lambda: datetime(2026, 4, 6, 15, tzinfo=timezone.utc))
    evening_due = client.get("/episodes/due", headers=auth_headers).json()["due"]
    assert len(evening_due) == 1
    assert evening_due[0]["episode_id"] == episode_id
    assert evening_due[0]["due_slot"] == "evening"
    assert evening_due[0]["missed_slots_today"] == []
    assert evening_due[0]["applications_completed_today"] == 1
    assert evening_due[0]["applications_expected_today"] == 2

    logged_evening = client.post(
        "/applications",
        headers=auth_headers,
        json={"episode_id": episode_id, "applied_at": "2026-04-06T16:30:00Z"},
    )
    assert logged_evening.status_code == 201
    assert client.get("/episodes/due", headers=auth_headers).json()["due"] == []


def test_phase_one_after_cutoff_marks_missed_morning_without_requiring_catchup(client, auth_headers, monkeypatch):
    import app.services as services

    episode = _create_episode(client, auth_headers, location_code="missed_morning", location_name="Missed morning")
    episode_id = episode["id"]

    monkeypatch.setattr(services, "utc_now", lambda: datetime(2026, 4, 6, 15, tzinfo=timezone.utc))
    due = client.get("/episodes/due", headers=auth_headers).json()["due"]
    assert len(due) == 1
    assert due[0]["episode_id"] == episode_id
    assert due[0]["due_slot"] == "evening"
    assert due[0]["missed_slots_today"] == ["morning"]
    assert due[0]["applications_completed_today"] == 0
    assert due[0]["applications_expected_today"] == 2

    logged_evening = client.post(
        "/applications",
        headers=auth_headers,
        json={"episode_id": episode_id, "applied_at": "2026-04-06T16:30:00Z"},
    )
    assert logged_evening.status_code == 201
    assert client.get("/episodes/due", headers=auth_headers).json()["due"] == []


def test_taper_due_returns_only_currently_due_items(client, auth_headers, monkeypatch):
    import app.services as services

    episode = _create_episode(client, auth_headers, location_code="taper_elbow", location_name="Taper elbow")
    episode_id = episode["id"]
    heal = client.post(f"/episodes/{episode_id}/heal", headers=auth_headers, json={"healed_at": "2026-04-05T08:00:00Z"})
    assert heal.status_code == 200

    monkeypatch.setattr(services, "utc_now", lambda: datetime(2026, 4, 6, 8, tzinfo=timezone.utc))
    assert client.get("/episodes/due", headers=auth_headers).json()["due"] == []

    monkeypatch.setattr(services, "utc_now", lambda: datetime(2026, 4, 7, 8, tzinfo=timezone.utc))
    due = client.get("/episodes/due", headers=auth_headers).json()["due"]
    assert len(due) == 1
    assert due[0]["episode_id"] == episode_id
    assert due[0]["current_phase_number"] == 2
    assert due[0]["due_slot"] is None
    assert due[0]["missed_slots_today"] == []
