from __future__ import annotations

from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.models import Account, BodyLocation, EczemaEpisode, EpisodePhaseHistory, Subject


def _create_episode(client, headers, *, subject_name: str = "Child", location_code: str = "left_elbow") -> dict:
    subject = client.post("/subjects", headers=headers, json={"display_name": subject_name}).json()
    location = client.post("/locations", headers=headers, json={"code": location_code, "display_name": location_code.replace("_", " ").title()}).json()
    created = client.post("/episodes", headers=headers, json={"subject_id": subject["id"], "location_id": location["location"]["id"]})
    episode = created.json()["episode"]
    db = SessionLocal()
    try:
        stored_episode = db.get(EczemaEpisode, episode["id"])
        stored_episode.phase_started_at = datetime(2026, 1, 1, 8, tzinfo=timezone.utc)
        history = db.query(EpisodePhaseHistory).filter(EpisodePhaseHistory.episode_id == episode["id"]).one()
        history.started_at = datetime(2026, 1, 1, 8, tzinfo=timezone.utc)
        db.add_all([stored_episode, history])
        db.commit()
    finally:
        db.close()
    return {"subject": subject, "location": location["location"], "episode": episode}


def _log_application(client, headers, episode_id: int, applied_at: str):
    return client.post(
        "/applications",
        headers=headers,
        json={"episode_id": episode_id, "applied_at": applied_at, "treatment_type": "steroid"},
    )


def test_adherence_endpoints_require_auth(client):
    endpoints = [
        ("GET", "/adherence/calendar?from=2026-01-01&to=2026-01-02"),
        ("GET", "/adherence/summary?from=2026-01-01&to=2026-01-02"),
        ("GET", "/adherence/missed?from=2026-01-01&to=2026-01-02"),
        ("GET", "/episodes/1/adherence?from=2026-01-01&to=2026-01-02"),
    ]
    for method, path in endpoints:
        response = client.request(method, path)
        assert response.status_code == 401

    rebuild = client.post("/adherence/rebuild", json={"from": "2026-01-01", "to": "2026-01-02"})
    assert rebuild.status_code == 401


def test_calendar_dynamic_by_default_and_persisted_requires_rebuild(client, auth_headers):
    setup = _create_episode(client, auth_headers)
    episode_id = setup["episode"]["id"]
    _log_application(client, auth_headers, episode_id, "2026-01-01T08:00:00Z")

    dynamic_default = client.get("/adherence/calendar?from=2026-01-01&to=2026-01-02", headers=auth_headers)
    assert dynamic_default.status_code == 200
    dynamic_days = dynamic_default.json()["days"]
    assert len(dynamic_days) == 2
    assert dynamic_days[0]["source"] == "calculated"
    assert dynamic_days[0]["status"] == "partial"
    assert dynamic_days[1]["status"] == "missed"

    dynamic_explicit = client.get("/adherence/calendar?from=2026-01-01&to=2026-01-02&persisted=false", headers=auth_headers)
    assert dynamic_explicit.status_code == 200
    explicit_days = dynamic_explicit.json()["days"]
    assert len(explicit_days) == len(dynamic_days)
    assert [(day["date"], day["status"], day["source"]) for day in explicit_days] == [
        (day["date"], day["status"], day["source"]) for day in dynamic_days
    ]

    persisted_before = client.get("/adherence/calendar?from=2026-01-01&to=2026-01-02&persisted=true", headers=auth_headers)
    assert persisted_before.status_code == 200
    assert persisted_before.json()["days"] == []

    rebuild = client.post(
        "/adherence/rebuild",
        headers=auth_headers,
        json={"episode_id": episode_id, "from": "2026-01-01", "to": "2026-01-02"},
    )
    assert rebuild.status_code == 200
    assert rebuild.json() == {"episodes_processed": 1, "rows_persisted": 2}

    persisted_after = client.get("/adherence/calendar?from=2026-01-01&to=2026-01-02&persisted=true", headers=auth_headers)
    assert persisted_after.status_code == 200
    persisted_days = persisted_after.json()["days"]
    assert len(persisted_days) == 2
    assert {day["source"] for day in persisted_days} == {"rebuild"}


def test_summary_missed_and_episode_adherence(client, auth_headers):
    setup = _create_episode(client, auth_headers)
    episode_id = setup["episode"]["id"]
    _log_application(client, auth_headers, episode_id, "2026-01-01T08:00:00Z")

    summary = client.get("/adherence/summary?from=2026-01-01&to=2026-01-02", headers=auth_headers)
    assert summary.status_code == 200
    assert summary.json() == {
        "from": "2026-01-01",
        "to": "2026-01-02",
        "expected_applications": 4,
        "completed_applications": 1,
        "credited_applications": 1,
        "adherence_score": 0.25,
        "completed_days": 0,
        "partial_days": 1,
        "missed_days": 1,
        "not_due_days": 0,
        "future_days": 0,
    }

    missed = client.get("/adherence/missed?from=2026-01-01&to=2026-01-02", headers=auth_headers)
    assert missed.status_code == 200
    assert [day["status"] for day in missed.json()["days"]] == ["missed"]

    missed_and_partial = client.get("/adherence/missed?from=2026-01-01&to=2026-01-02&include_partial=true", headers=auth_headers)
    assert missed_and_partial.status_code == 200
    assert [day["status"] for day in missed_and_partial.json()["days"]] == ["partial", "missed"]

    episode_adherence = client.get(f"/episodes/{episode_id}/adherence?from=2026-01-01&to=2026-01-02", headers=auth_headers)
    assert episode_adherence.status_code == 200
    payload = episode_adherence.json()
    assert payload["episode_id"] == episode_id
    assert payload["from"] == "2026-01-01"
    assert payload["to"] == "2026-01-02"
    assert payload["summary"]["adherence_score"] == 0.25
    assert len(payload["days"]) == 2


def test_episode_subject_and_location_filters(client, auth_headers):
    first = _create_episode(client, auth_headers, subject_name="Child A", location_code="left_elbow")
    second = _create_episode(client, auth_headers, subject_name="Child B", location_code="right_elbow")

    first_episode_id = first["episode"]["id"]
    second_episode_id = second["episode"]["id"]
    subject_id = first["subject"]["id"]
    location_id = first["location"]["id"]

    by_episode = client.get(f"/adherence/calendar?episode_id={first_episode_id}&from=2026-01-01&to=2026-01-01", headers=auth_headers)
    assert by_episode.status_code == 200
    assert {day["episode_id"] for day in by_episode.json()["days"]} == {first_episode_id}

    by_subject = client.get(f"/adherence/calendar?subject_id={subject_id}&from=2026-01-01&to=2026-01-01", headers=auth_headers)
    assert by_subject.status_code == 200
    assert {day["episode_id"] for day in by_subject.json()["days"]} == {first_episode_id}

    by_location = client.get(f"/adherence/calendar?location_id={location_id}&from=2026-01-01&to=2026-01-01", headers=auth_headers)
    assert by_location.status_code == 200
    assert {day["episode_id"] for day in by_location.json()["days"]} == {first_episode_id}

    mismatch = client.get(
        f"/adherence/calendar?episode_id={first_episode_id}&location_id={second['location']['id']}&from=2026-01-01&to=2026-01-01",
        headers=auth_headers,
    )
    assert mismatch.status_code == 200
    assert mismatch.json()["days"] == []

    all_rows = client.get("/adherence/calendar?from=2026-01-01&to=2026-01-01", headers=auth_headers)
    assert all_rows.status_code == 200
    assert {day["episode_id"] for day in all_rows.json()["days"]} == {first_episode_id, second_episode_id}


def test_unknown_and_cross_account_episode_access(client, auth_headers):
    unknown = client.get("/adherence/calendar?episode_id=9999&from=2026-01-01&to=2026-01-01", headers=auth_headers)
    assert unknown.status_code == 404

    db = SessionLocal()
    try:
        other = Account(username="other", password_hash=hash_password("other"), is_active=True)
        db.add(other)
        db.flush()
        subject = Subject(account_id=other.id, display_name="Other child")
        location = BodyLocation(account_id=other.id, code="other_elbow", display_name="Other elbow")
        db.add_all([subject, location])
        db.flush()
        other_episode = EczemaEpisode(
            account_id=other.id,
            subject_id=subject.id,
            location_id=location.id,
            status="active_flare",
            current_phase_number=1,
            phase_started_at=datetime(2026, 1, 1, 8, tzinfo=timezone.utc),
            phase_due_end_at=None,
            protocol_version="v1",
        )
        db.add(other_episode)
        db.flush()
        db.add(
            EpisodePhaseHistory(
                episode_id=other_episode.id,
                phase_number=1,
                started_at=datetime(2026, 1, 1, 8, tzinfo=timezone.utc),
                ended_at=None,
                reason="episode_created",
            )
        )
        other_episode_id = other_episode.id
        other_subject_id = subject.id
        other_location_id = location.id
        other_token = create_access_token(subject=str(other.id), account_id=other.id)
        db.commit()
    finally:
        db.close()

    other_access = client.get(
        f"/adherence/calendar?episode_id={other_episode_id}&from=2026-01-01&to=2026-01-01",
        headers=auth_headers,
    )
    assert other_access.status_code == 404

    subject_filter = client.get(f"/adherence/calendar?subject_id={other_subject_id}&from=2026-01-01&to=2026-01-01", headers=auth_headers)
    assert subject_filter.status_code == 200
    assert subject_filter.json()["days"] == []

    location_filter = client.get(f"/adherence/calendar?location_id={other_location_id}&from=2026-01-01&to=2026-01-01", headers=auth_headers)
    assert location_filter.status_code == 200
    assert location_filter.json()["days"] == []

    other_account_access = client.get(
        f"/adherence/calendar?episode_id={other_episode_id}&from=2026-01-01&to=2026-01-01",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert other_account_access.status_code == 200
    assert len(other_account_access.json()["days"]) == 1


def test_invalid_date_range_returns_422(client, auth_headers):
    response = client.get("/adherence/calendar?from=2026-01-03&to=2026-01-01", headers=auth_headers)
    assert response.status_code == 422
    assert response.json()["error"]["message"] == "invalid date range"


def test_rebuild_active_excludes_obsolete_and_rejects_all_episode_mode(client, auth_headers):
    active = _create_episode(client, auth_headers, subject_name="Active child", location_code="active_elbow")
    obsolete = _create_episode(client, auth_headers, subject_name="Old child", location_code="old_elbow")

    db = SessionLocal()
    try:
        obsolete_episode = db.get(EczemaEpisode, obsolete["episode"]["id"])
        obsolete_episode.status = "obsolete"
        db.add(obsolete_episode)
        db.commit()
    finally:
        db.close()

    rejected = client.post(
        "/adherence/rebuild",
        headers=auth_headers,
        json={"from": "2026-01-01", "to": "2026-01-01", "active_only": False},
    )
    assert rejected.status_code == 422

    rebuilt = client.post("/adherence/rebuild", headers=auth_headers, json={"from": "2026-01-01", "to": "2026-01-01"})
    assert rebuilt.status_code == 200
    assert rebuilt.json() == {"episodes_processed": 1, "rows_persisted": 1}

    persisted = client.get("/adherence/calendar?from=2026-01-01&to=2026-01-01&persisted=true", headers=auth_headers)
    assert persisted.status_code == 200
    assert [day["episode_id"] for day in persisted.json()["days"]] == [active["episode"]["id"]]
