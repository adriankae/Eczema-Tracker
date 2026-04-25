from __future__ import annotations


def _episode(client, headers):
    subject = client.post("/subjects", headers=headers, json={"display_name": "Child"}).json()["id"]
    location = client.post("/locations", headers=headers, json={"code": "neck", "display_name": "Neck"}).json()["location"]["id"]
    episode = client.post("/episodes", headers=headers, json={"subject_id": subject, "location_id": location}).json()["episode"]
    client.post(f"/episodes/{episode['id']}/heal", headers=headers, json={"healed_at": "2026-04-05T18:00:00Z"})
    return episode["id"]


def test_application_crud_and_due(client, auth_headers):
    episode_id = _episode(client, auth_headers)
    minimal = client.post(
        "/applications",
        headers=auth_headers,
        json={
            "episode_id": episode_id,
            "applied_at": "2026-04-06T06:30:00Z",
        },
    )
    assert minimal.status_code == 201
    assert minimal.json()["application"]["treatment_type"] == "other"
    assert minimal.json()["application"]["treatment_name"] is None
    assert minimal.json()["application"]["quantity_text"] is None
    assert minimal.json()["application"]["notes"] is None

    created = client.post(
        "/applications",
        headers=auth_headers,
        json={
            "episode_id": episode_id,
            "applied_at": "2026-04-06T07:30:00Z",
            "treatment_type": "steroid",
            "treatment_name": "Hydrocortisone 1%",
            "quantity_text": "thin layer",
            "notes": "morning dose",
        },
    )
    assert created.status_code == 201
    application_id = created.json()["application"]["id"]

    duplicate = client.post(
        "/applications",
        headers=auth_headers,
        json={
            "episode_id": episode_id,
            "applied_at": "2026-04-06T07:30:00Z",
            "treatment_type": "steroid",
        },
    )
    assert duplicate.status_code == 409

    updated = client.patch(f"/applications/{application_id}", headers=auth_headers, json={"notes": "updated"})
    assert updated.status_code == 200
    assert updated.json()["application"]["notes"] == "updated"

    deleted = client.delete(f"/applications/{application_id}", headers=auth_headers)
    assert deleted.status_code == 200

    due = client.get("/episodes/due", headers=auth_headers)
    assert due.status_code == 200
    assert isinstance(due.json()["due"], list)
