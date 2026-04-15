from __future__ import annotations


def test_events_are_emitted(client, auth_headers):
    subject = client.post("/subjects", headers=auth_headers, json={"display_name": "Child"}).json()["id"]
    location = client.post("/locations", headers=auth_headers, json={"code": "glabella", "display_name": "Glabella"}).json()["location"]["id"]
    episode = client.post("/episodes", headers=auth_headers, json={"subject_id": subject, "location_id": location}).json()["episode"]
    events = client.get(f"/episodes/{episode['id']}/events", headers=auth_headers)
    assert events.status_code == 200
    types = [event["event_type"] for event in events.json()["events"]]
    assert "episode_created" in types
