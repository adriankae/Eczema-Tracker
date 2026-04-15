from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./eczema_test.db")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEPLOYMENT_TIMEZONE", "UTC")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ENABLE_SCHEDULER", "false")
os.environ.setdefault("INITIAL_USERNAME", "admin")
os.environ.setdefault("INITIAL_PASSWORD", "admin")

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.models import Account
from app.core.security import hash_password


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        from app.services import bootstrap_data

        bootstrap_data(db)
    finally:
        db.close()
    yield


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth_headers(client):
    response = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
