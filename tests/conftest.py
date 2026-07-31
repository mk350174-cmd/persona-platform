"""Shared fixtures for the api/ test suite (T2-012).

Sets DATABASE_URL to a throwaway SQLite file *before* api.db is imported,
so tests never touch the dev persona_platform.db used by manual runs.
"""
from __future__ import annotations

import os
import tempfile

_tmp_fd, _tmp_db_path = tempfile.mkstemp(suffix=".db")
os.close(_tmp_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db_path}"
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_dummy")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.db import Base, engine  # noqa: E402
from api.main import app  # noqa: E402
from api.rate_limit import limiter  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    limiter.reset()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers(client):
    client.post("/auth/register", json={"email": "fixture@example.com", "password": "testpass123", "date_of_birth": "1990-01-01"})
    r = client.post("/auth/login", json={"email": "fixture@example.com", "password": "testpass123", "date_of_birth": "1990-01-01"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
