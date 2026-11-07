"""NEXUS backend entrypoint. Phase 2: auth, stats, health."""

from __future__ import annotations

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import get_current_user, router as auth_router
from .chat import router as chat_router
from .database import SessionLocal, get_session, init_db
from .documents import router as documents_router
from .models import AuditEvent, ChatHistory, Chunk, Document, SecurityEvent, User
from .security import router as security_router

app = FastAPI(title="NEXUS")

FRONTEND_ORIGINS = [
    o.strip()
    for o in os.environ.get("FRONTEND_URL", "http://localhost:5173").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(security_router)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "nexus"}


@app.get("/me")
def me_alias(current: User = Depends(get_current_user)) -> dict:
    """Top-level /me alias (canonical route is /auth/me)."""
    return {"username": current.username, "role": current.role, "department": current.department}


@app.get("/stats/summary")
def stats_summary(db: Session = Depends(get_session)) -> dict:
    counts = {}
    for name, model in (
        ("users", User),
        ("documents", Document),
        ("chunks", Chunk),
        ("audit_events", AuditEvent),
        ("security_events", SecurityEvent),
        ("chat_history", ChatHistory),
    ):
        counts[name] = db.scalar(select(func.count()).select_from(model)) or 0
    return counts


def _seed_demo_users_if_empty() -> None:
    """Ensure demo users exist for local dev (idempotent)."""
    from .auth import DEMO_USERS, hash_password

    db = SessionLocal()
    try:
        existing = {u.username for u in db.scalars(select(User)).all()}
        for username, (password, role, dept) in DEMO_USERS.items():
            if username not in existing:
                db.add(
                    User(
                        username=username,
                        password_hash=hash_password(password),
                        role=role,
                        department=dept,
                    )
                )
        db.commit()
    finally:
        db.close()
