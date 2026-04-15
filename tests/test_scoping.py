from __future__ import annotations

from app.core.security import create_access_token, hash_password
from app.core.database import SessionLocal
from app.models import Account, BodyLocation, Subject


def test_cross_account_access_is_blocked(client, auth_headers):
    db = SessionLocal()
    try:
        other = Account(username="other", password_hash=hash_password("other"), is_active=True)
        db.add(other)
        db.flush()
        subject = Subject(account_id=other.id, display_name="Other child")
        location = BodyLocation(account_id=other.id, code="other_elbow", display_name="Other elbow")
        db.add_all([subject, location])
        db.flush()
        subject_id = subject.id
        db.commit()

        other_token = create_access_token(subject=str(other.id), account_id=other.id)
    finally:
        db.close()

    response = client.get(f"/subjects/{subject_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert response.status_code == 200

    forbidden = client.get(f"/subjects/{subject_id}", headers=auth_headers)
    assert forbidden.status_code == 404
