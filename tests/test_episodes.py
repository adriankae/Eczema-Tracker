from __future__ import annotations

from datetime import datetime, timezone


def _create_subject_location(client, headers):
    subject = client.post("/subjects", headers=headers, json={"display_name": "Child"}).json()
    location = client.post("/locations", headers=headers, json={"code": "left_elbow", "display_name": "Left elbow"}).json()
    return subject["id"], location["location"]["id"]


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
