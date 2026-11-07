"""test_12: default DATABASE_URL is anchored to the repo root, not the cwd.

Regression test: a relative default (sqlite:///./nexus.db) silently selected a
different database depending on where uvicorn/pytest was launched, so logins
failed with 401 and an empty database file was created in the launch cwd.
"""

import os


def test_default_db_url_is_absolute_and_repo_rooted(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from app import config

    url = config._default_db_url()
    assert url.startswith("sqlite:///"), url
    path = url.removeprefix("sqlite:///")
    assert os.path.isabs(path), url
    assert os.path.basename(path) == "nexus.db"
    # The resolved directory must be the repo root (it contains backend/app).
    assert os.path.isdir(os.path.join(os.path.dirname(path), "backend", "app"))


def test_explicit_database_url_wins(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/nexus-custom.db")
    from app import config

    assert config._default_db_url() == "sqlite:////tmp/nexus-custom.db"
