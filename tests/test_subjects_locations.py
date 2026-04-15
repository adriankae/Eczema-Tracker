from __future__ import annotations


def test_subject_and_location_creation(client, auth_headers):
    subject = client.post("/subjects", headers=auth_headers, json={"display_name": "Child"})
    assert subject.status_code == 201
    assert subject.json()["display_name"] == "Child"

    location = client.post("/locations", headers=auth_headers, json={"code": "left_elbow", "display_name": "Left elbow"})
    assert location.status_code == 201
    assert location.json()["location"]["code"] == "left_elbow"
