"""NEXUS backend settings. Env-based, no secrets in code."""

from __future__ import annotations

import os
import warnings


def _default_db_url() -> str:
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    # Anchor the default DB to the repo root (parent of backend/) so the
    # working directory never selects a different database file.
    root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    return f"sqlite:///{os.path.join(root, 'nexus.db')}"


def get_encryption_key() -> str:
    """Return ENCRYPTION_KEY from env, or a dev fallback with a warning."""
    key = os.environ.get("ENCRYPTION_KEY")
    if not key or key == "REPLACE_WITH_GENERATED_FERNET_KEY":
        warnings.warn(
            "ENCRYPTION_KEY not set: using insecure dev fallback key. "
            "Set ENCRYPTION_KEY in production.",
            RuntimeWarning,
            stacklevel=2,
        )
        return "nexus-dev-fallback-key-DO-NOT-USE-IN-PROD"
    return key


class Settings:
    """Lightweight env-based settings (no extra deps beyond stdlib)."""

    def __init__(self) -> None:
        self.database_url: str = _default_db_url()
        self.llm_provider: str = os.environ.get("LLM_PROVIDER", "mock")
        self.embedding_provider: str = os.environ.get("EMBEDDING_PROVIDER", "local")
        self.jwt_secret: str = os.environ.get(
            "JWT_SECRET", "nexus-dev-jwt-secret-CHANGE-ME-32bytes-min!!"
        )
        self.jwt_algorithm: str = os.environ.get("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes: int = int(
            os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        )

    @property
    def encryption_key(self) -> str:
        return get_encryption_key()


settings = Settings()
