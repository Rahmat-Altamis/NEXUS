"""Shared pytest fixtures: isolated test DB, seeded dataset, TestClient.

Mirrors frontend client usage (see frontend/src/lib/api.ts): login via
POST /auth/login, Bearer token, POST /chat with {message, lang, allow_pii}.
"""

from __future__ import annotations

import base64
import os
import sys
import tempfile

# Isolated test DB + fixed test secrets BEFORE importing the app (the app
# creates its engine from DATABASE_URL at import time).
_TEST_DIR = tempfile.mkdtemp(prefix="nexus_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DIR}/test.db"
os.environ["ENCRYPTION_KEY"] = base64.b64encode(b"0123456789abcdef0123456789abcdef").decode()
os.environ["JWT_SECRET"] = "test-jwt-secret-32bytes-minimum!!"
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("EMBEDDING_PROVIDER", "local")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.auth import DEMO_USERS  # noqa: E402
from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402
from seed_data import seed_all  # noqa: E402


@pytest.fixture(scope="session")
def seeded_ids() -> dict:
    """Seed users + full synthetic dataset once into the isolated test DB."""
    init_db()
    seed_all()
    from app.database import SessionLocal
    from sqlalchemy import select
    from app.models import Document
    db = SessionLocal()
    try:
        return {d.filename: d.id for d in db.scalars(select(Document)).all()}
    finally:
        db.close()


@pytest.fixture(scope="session")
def client(seeded_ids) -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def tokens(client: TestClient) -> dict:
    """Username -> Authorization header dict."""
    out = {}
    for username, (password, _role, _dept) in DEMO_USERS.items():
        resp = client.post("/auth/login", json={"username": username, "password": password})
        assert resp.status_code == 200, resp.text
        out[username] = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    return out


def auth(tokens: dict, username: str) -> dict:
    return tokens[username]


def chat(client: TestClient, headers: dict, message: str, lang: str = "id", allow_pii: bool = False) -> dict:
    resp = client.post("/chat", json={"message": message, "lang": lang, "allow_pii": allow_pii}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()
