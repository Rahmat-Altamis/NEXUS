"""Seed demo users + a couple of test docs. Idempotent.

Usage: python nexus/scripts/seed_users.py  (run from repo root /home/nabil/nexus)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select  # noqa: E402

from app.auth import DEMO_USERS, hash_password  # noqa: E402
from app.crypto import encrypt_bytes  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402
from app.models import Chunk, Document, User  # noqa: E402

TEST_DOCS = [
    {
        "filename": "engineering-handbook.txt",
        "source_type": "seed",
        "department": "engineering",
        "author": "budi",
        "effective_date": "2026-01-01",
        "version": "1.0",
        "status": "active",
        "access_policy": {},
        "content": "NEXUS engineering handbook (synthetic). Deploy checklist: tests pass, review done.",
    },
    {
        "filename": "hr-leave-policy.txt",
        "source_type": "seed",
        "department": "hr",
        "author": "hana",
        "effective_date": "2026-01-01",
        "version": "1.0",
        "status": "active",
        "access_policy": {"allowed_departments": ["hr"]},
        "content": "NEXUS HR leave policy (synthetic). Annual leave: 12 days, request via manager.",
    },
]


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        existing_users = {u.username for u in db.scalars(select(User)).all()}
        for username, (password, role, dept) in DEMO_USERS.items():
            if username not in existing_users:
                db.add(
                    User(
                        username=username,
                        password_hash=hash_password(password),
                        role=role,
                        department=dept,
                    )
                )
        existing_docs = {d.filename for d in db.scalars(select(Document)).all()}
        for spec in TEST_DOCS:
            if spec["filename"] in existing_docs:
                continue
            doc = Document(
                filename=spec["filename"],
                source_type=spec["source_type"],
                department=spec["department"],
                author=spec["author"],
                effective_date=spec["effective_date"],
                version=spec["version"],
                status=spec["status"],
                access_policy=spec["access_policy"],
                content_encrypted=encrypt_bytes(spec["content"].encode("utf-8")),
            )
            db.add(doc)
            db.flush()
            db.add(
                Chunk(
                    doc_id=doc.id,
                    idx=0,
                    text_encrypted=encrypt_bytes(spec["content"].encode("utf-8")),
                    embedding=None,
                    provenance={"filename": spec["filename"], "idx": 0},
                )
            )
        db.commit()
        n_users = len(db.scalars(select(User)).all())
        n_docs = len(db.scalars(select(Document)).all())
        print(f"seed ok: users={n_users} docs={n_docs}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
