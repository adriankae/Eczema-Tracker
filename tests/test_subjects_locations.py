from __future__ import annotations

from datetime import date, datetime, timezone

from app.core.database import SessionLocal
from app.models import (
    BodyLocation,
    EczemaEpisode,
    EpisodeDailyAdherence,
    EpisodeEvent,
    EpisodePhaseHistory,
    Subject,
    TreatmentApplication,
)


def test_subject_and_location_creation(client, auth_headers):
    subject = client.post("/subjects", headers=auth_headers, json={"display_name": "Child"})
    assert subject.status_code == 201
    assert subject.json()["display_name"] == "Child"

    location = client.post("/locations", headers=auth_headers, json={"code": "left_elbow", "display_name": "Left elbow"})
    assert location.status_code == 201
    assert location.json()["location"]["code"] == "left_elbow"


def test_delete_subject_without_episodes(client, auth_headers):
    subject = client.post("/subjects", headers=auth_headers, json={"display_name": "Temporary child"}).json()

    deleted = client.delete(f"/subjects/{subject['id']}", headers=auth_headers)
    assert deleted.status_code == 200
    assert deleted.json()["display_name"] == "Temporary child"

    missing = client.get(f"/subjects/{subject['id']}", headers=auth_headers)
    assert missing.status_code == 404


def test_delete_subject_with_episode_cascades_subject_owned_data(client, auth_headers):
    subject = client.post("/subjects", headers=auth_headers, json={"display_name": "Child"}).json()
    location = client.post("/locations", headers=auth_headers, json={"code": "left_elbow", "display_name": "Left elbow"}).json()
    episode = client.post(
        "/episodes",
        headers=auth_headers,
        json={"subject_id": subject["id"], "location_id": location["location"]["id"]},
    )
    assert episode.status_code == 201
    episode_id = episode.json()["episode"]["id"]

    application = client.post(
        "/applications",
        headers=auth_headers,
        json={"episode_id": episode_id, "applied_at": "2026-04-06T06:30:00Z"},
    )
    assert application.status_code == 201

    other_subject = client.post("/subjects", headers=auth_headers, json={"display_name": "Sibling"}).json()
    other_episode = client.post(
        "/episodes",
        headers=auth_headers,
        json={"subject_id": other_subject["id"], "location_id": location["location"]["id"]},
    )
    assert other_episode.status_code == 201
    other_episode_id = other_episode.json()["episode"]["id"]
    other_application = client.post(
        "/applications",
        headers=auth_headers,
        json={"episode_id": other_episode_id, "applied_at": "2026-04-06T07:30:00Z"},
    )
    assert other_application.status_code == 201

    db = SessionLocal()
    try:
        target_episode = db.get(EczemaEpisode, episode_id)
        other_stored_episode = db.get(EczemaEpisode, other_episode_id)
        assert target_episode is not None
        assert other_stored_episode is not None
        db.add_all(
            [
                EpisodeDailyAdherence(
                    account_id=target_episode.account_id,
                    episode_id=episode_id,
                    subject_id=subject["id"],
                    location_id=location["location"]["id"],
                    date=date(2026, 4, 6),
                    phase_number=1,
                    expected_applications=2,
                    completed_applications=1,
                    credited_applications=1,
                    status="partial",
                    source="rebuild",
                    calculated_at=datetime(2026, 4, 6, 23, 0, tzinfo=timezone.utc),
                ),
                EpisodeDailyAdherence(
                    account_id=other_stored_episode.account_id,
                    episode_id=other_episode_id,
                    subject_id=other_subject["id"],
                    location_id=location["location"]["id"],
                    date=date(2026, 4, 6),
                    phase_number=1,
                    expected_applications=2,
                    completed_applications=1,
                    credited_applications=1,
                    status="partial",
                    source="rebuild",
                    calculated_at=datetime(2026, 4, 6, 23, 0, tzinfo=timezone.utc),
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    deleted = client.delete(f"/subjects/{subject['id']}", headers=auth_headers)
    assert deleted.status_code == 200
    assert deleted.json()["display_name"] == "Child"

    subjects = client.get("/subjects", headers=auth_headers)
    assert subjects.status_code == 200
    subject_ids = {item["id"] for item in subjects.json()["subjects"]}
    assert subject["id"] not in subject_ids
    assert other_subject["id"] in subject_ids

    episodes = client.get("/episodes", headers=auth_headers)
    assert episodes.status_code == 200
    episode_ids = {item["id"] for item in episodes.json()["episodes"]}
    assert episode_id not in episode_ids
    assert other_episode_id in episode_ids

    due = client.get("/episodes/due", headers=auth_headers)
    assert due.status_code == 200
    due_episode_ids = {item["episode_id"] for item in due.json()["due"]}
    assert episode_id not in due_episode_ids

    db = SessionLocal()
    try:
        assert db.get(Subject, subject["id"]) is None
        assert db.get(EczemaEpisode, episode_id) is None
        assert db.query(TreatmentApplication).filter(TreatmentApplication.episode_id == episode_id).count() == 0
        assert db.query(EpisodePhaseHistory).filter(EpisodePhaseHistory.episode_id == episode_id).count() == 0
        assert db.query(EpisodeEvent).filter(EpisodeEvent.episode_id == episode_id).count() == 0
        assert db.query(EpisodeDailyAdherence).filter(EpisodeDailyAdherence.episode_id == episode_id).count() == 0
        assert db.query(EpisodeDailyAdherence).filter(EpisodeDailyAdherence.subject_id == subject["id"]).count() == 0

        assert db.get(BodyLocation, location["location"]["id"]) is not None
        assert db.get(Subject, other_subject["id"]) is not None
        assert db.get(EczemaEpisode, other_episode_id) is not None
        assert db.query(TreatmentApplication).filter(TreatmentApplication.episode_id == other_episode_id).count() == 1
        assert db.query(EpisodeDailyAdherence).filter(EpisodeDailyAdherence.episode_id == other_episode_id).count() == 1
    finally:
        db.close()


def test_delete_unknown_subject_returns_404(client, auth_headers):
    response = client.delete("/subjects/99999", headers=auth_headers)
    assert response.status_code == 404
