from __future__ import annotations


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


def test_delete_subject_with_episode_is_blocked(client, auth_headers):
    subject = client.post("/subjects", headers=auth_headers, json={"display_name": "Child"}).json()
    location = client.post("/locations", headers=auth_headers, json={"code": "left_elbow", "display_name": "Left elbow"}).json()
    episode = client.post(
        "/episodes",
        headers=auth_headers,
        json={"subject_id": subject["id"], "location_id": location["location"]["id"]},
    )
    assert episode.status_code == 201

    deleted = client.delete(f"/subjects/{subject['id']}", headers=auth_headers)
    assert deleted.status_code == 409
    assert deleted.json()["error"]["message"] == "subject has related episodes"

    still_present = client.get(f"/subjects/{subject['id']}", headers=auth_headers)
    assert still_present.status_code == 200


def test_delete_unknown_subject_returns_404(client, auth_headers):
    response = client.delete("/subjects/99999", headers=auth_headers)
    assert response.status_code == 404
