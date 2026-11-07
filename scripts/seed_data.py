"""Seed the full synthetic dataset (Nusantara Digital Group, all fictitious).

Ingests every file under nexus/data/synthetic/{docs,chats,tasks} through the
real ingest service with the per-file policy from MANIFEST. Idempotent: files
already present (matched by filename) are skipped.

Usage:  python nexus/scripts/seed_data.py   (run from repo root /home/nabil/nexus)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select  # noqa: E402

from app.auth import DEMO_USERS, hash_password  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402
from app.ingest import ingest_file  # noqa: E402
from app.models import Document, User  # noqa: E402

DATA_ROOT = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic")

PUBLIC = {"allowed_roles": ["admin", "manager", "hr", "finance", "employee"]}
HR_ONLY = {"allowed_roles": ["admin", "hr"]}
FIN_ONLY = {"allowed_roles": ["admin", "finance"]}
MGR_ONLY = {"allowed_roles": ["admin", "manager"]}
GARUDA = {"allowed_users": ["siti", "budi"]}
ENG_DEPT = {"allowed_departments": ["engineering"]}

# (subdir, filename) -> ingest metadata
MANIFEST: dict[tuple[str, str], dict] = {
    ("docs", "hr-leave-policy-v1.md"): {"department": "hr", "author": "hana", "effective_date": "2025-06-01", "version": "1.0", "access_policy": PUBLIC, "authority": "sop"},
    ("docs", "hr-leave-policy-v2.md"): {"department": "hr", "author": "hana", "effective_date": "2026-02-01", "version": "2.0", "access_policy": PUBLIC, "authority": "sop"},
    ("docs", "transport-allowance-sop.md"): {"department": "hr", "author": "hana", "effective_date": "2026-01-15", "version": "1.0", "access_policy": PUBLIC, "authority": "sop"},
    ("docs", "transport-allowance-announcement.md"): {"department": "hr", "author": "hana", "effective_date": "2026-03-10", "version": "1.1", "access_policy": PUBLIC, "authority": "announcement"},
    ("docs", "wfh-policy-v1.md"): {"department": "it", "author": "agus", "effective_date": "2026-01-20", "version": "1.0", "access_policy": PUBLIC, "authority": "sop"},
    ("docs", "wfh-policy-v2.md"): {"department": "hr", "author": "hana", "effective_date": "2026-04-05", "version": "2.0", "access_policy": PUBLIC, "authority": "sop"},
    ("docs", "onboarding-checklist-v1.md"): {"department": "hr", "author": "hana", "effective_date": "2026-01-10", "version": "1.0", "access_policy": PUBLIC, "authority": "sop"},
    ("docs", "onboarding-checklist-v2.md"): {"department": "hr", "author": "hana", "effective_date": "2026-03-22", "version": "2.0", "access_policy": PUBLIC, "authority": "sop"},
    ("docs", "onboarding-guide.md"): {"department": "hr", "author": "hana", "effective_date": "2026-02-01", "version": "1.0", "access_policy": PUBLIC, "authority": "panduan"},
    ("docs", "it-security-policy.md"): {"department": "it", "author": "agus", "effective_date": "2026-01-05", "version": "1.0", "access_policy": PUBLIC, "authority": "policy"},
    ("docs", "general-office-sop.md"): {"department": "general", "author": "agus", "effective_date": "2026-01-05", "version": "1.0", "access_policy": PUBLIC, "authority": "sop"},
    ("docs", "office-event-announcement.md"): {"department": "general", "author": "siti", "effective_date": "2026-05-01", "version": "1.0", "access_policy": PUBLIC, "authority": "announcement"},
    ("docs", "employee-directory.md"): {"department": "hr", "author": "hana", "effective_date": "2026-04-15", "version": "1.0", "access_policy": PUBLIC, "authority": "directory"},
    ("docs", "project-garuda-charter.md"): {"department": "engineering", "author": "budi", "effective_date": "2026-02-10", "version": "1.0", "access_policy": GARUDA, "authority": "charter"},
    ("docs", "finance-expense-memo.md"): {"department": "finance", "author": "dewi", "effective_date": "2026-01-05", "version": "1.0", "access_policy": FIN_ONLY, "authority": "memo"},
    ("docs", "finance-expense-sop.md"): {"department": "finance", "author": "dewi", "effective_date": "2026-04-01", "version": "2.0", "access_policy": FIN_ONLY, "authority": "sop"},
    ("docs", "finance-quarterly-report.md"): {"department": "finance", "author": "dewi", "effective_date": "2026-04-20", "version": "1.0", "access_policy": FIN_ONLY, "authority": "report"},
    ("docs", "hr-salary-records.md"): {"department": "hr", "author": "hana", "effective_date": "2026-03-01", "version": "1.0", "access_policy": HR_ONLY, "authority": "record"},
    ("docs", "hr-compensation-memo.md"): {"department": "hr", "author": "hana", "effective_date": "2026-03-15", "version": "1.0", "access_policy": HR_ONLY, "authority": "memo"},
    ("docs", "manager-performance-review.md"): {"department": "engineering", "author": "budi", "effective_date": "2026-04-10", "version": "1.0", "access_policy": MGR_ONLY, "authority": "review"},
    ("docs", "project-komodo-brief.md"): {"department": "engineering", "author": "budi", "effective_date": "2026-03-01", "version": "1.0", "access_policy": ENG_DEPT, "authority": "brief"},
    ("docs", "it-acceptable-use-policy.txt"): {"department": "it", "author": "agus", "effective_date": "2026-01-08", "version": "1.0", "access_policy": PUBLIC, "authority": "policy"},
    ("docs", "sop-archive-note.txt"): {"department": "general", "author": "agus", "effective_date": "2026-01-08", "version": "1.0", "access_policy": PUBLIC, "authority": "note"},
    ("docs", "policy-faq.json"): {"department": "general", "author": "agus", "effective_date": "2026-02-15", "version": "1.0", "access_policy": PUBLIC, "authority": "faq"},
    ("chats", "chat-garuda-01.json"): {"department": "engineering", "author": "budi", "effective_date": "2026-04-02", "version": "1.0", "access_policy": GARUDA, "authority": "chat"},
    ("chats", "chat-garuda-02.json"): {"department": "engineering", "author": "budi", "effective_date": "2026-04-09", "version": "1.0", "access_policy": GARUDA, "authority": "chat"},
    ("chats", "chat-garuda-03.json"): {"department": "engineering", "author": "budi", "effective_date": "2026-04-16", "version": "1.0", "access_policy": GARUDA, "authority": "chat"},
    ("chats", "chat-komodo-01.json"): {"department": "engineering", "author": "budi", "effective_date": "2026-04-03", "version": "1.0", "access_policy": ENG_DEPT, "authority": "chat"},
    ("chats", "chat-komodo-02.json"): {"department": "engineering", "author": "budi", "effective_date": "2026-04-10", "version": "1.0", "access_policy": ENG_DEPT, "authority": "chat"},
    ("chats", "chat-general-01.json"): {"department": "general", "author": "hana", "effective_date": "2026-04-04", "version": "1.0", "access_policy": PUBLIC, "authority": "chat"},
    ("chats", "chat-general-02.json"): {"department": "general", "author": "hana", "effective_date": "2026-04-05", "version": "1.0", "access_policy": PUBLIC, "authority": "chat"},
    ("chats", "chat-general-03.json"): {"department": "general", "author": "budi", "effective_date": "2026-04-06", "version": "1.0", "access_policy": PUBLIC, "authority": "chat"},
    ("chats", "chat-general-04.json"): {"department": "general", "author": "agus", "effective_date": "2026-04-07", "version": "1.0", "access_policy": PUBLIC, "authority": "chat"},
    ("chats", "chat-general-05.json"): {"department": "general", "author": "dewi", "effective_date": "2026-04-08", "version": "1.0", "access_policy": PUBLIC, "authority": "chat"},
    ("tasks", "tasks-garuda.json"): {"department": "engineering", "author": "budi", "effective_date": "2026-04-16", "version": "1.0", "access_policy": GARUDA, "authority": "task"},
    ("tasks", "tasks-komodo.csv"): {"department": "engineering", "author": "budi", "effective_date": "2026-04-10", "version": "1.0", "access_policy": ENG_DEPT, "authority": "task"},
    ("tasks", "tasks-office.csv"): {"department": "general", "author": "agus", "effective_date": "2026-04-07", "version": "1.0", "access_policy": PUBLIC, "authority": "task"},
    ("tasks", "tasks-finance.json"): {"department": "finance", "author": "dewi", "effective_date": "2026-04-30", "version": "1.0", "access_policy": FIN_ONLY, "authority": "task"},
}


def ensure_users(db) -> int:
    existing = {u.username for u in db.scalars(select(User)).all()}
    added = 0
    for username, (password, role, dept) in DEMO_USERS.items():
        if username not in existing:
            db.add(User(username=username, password_hash=hash_password(password), role=role, department=dept))
            added += 1
    db.commit()
    return added


def seed_all(data_root: str = DATA_ROOT) -> dict:
    """Seed users + dataset into the configured DB. Returns counts."""
    init_db()
    db = SessionLocal()
    try:
        users_added = ensure_users(db)
        existing = {d.filename for d in db.scalars(select(Document)).all()}
        ingested, skipped = 0, 0
        for (subdir, filename), meta in MANIFEST.items():
            if filename in existing:
                skipped += 1
                continue
            path = os.path.join(data_root, subdir, filename)
            with open(path, "rb") as fh:
                content = fh.read()
            ingest_file(
                db, filename, content,
                department=meta["department"], author=meta["author"],
                effective_date=meta["effective_date"], version=meta["version"],
                access_policy=dict(meta["access_policy"]), authority=meta["authority"],
            )
            ingested += 1
        n_docs = db.scalar(select(Document.id).limit(1)) is not None and len(db.scalars(select(Document)).all()) or 0
        return {"users_added": users_added, "ingested": ingested, "skipped": skipped, "total_docs": n_docs}
    finally:
        db.close()


def main() -> None:
    result = seed_all()
    print(f"seed ok: users_added={result['users_added']} ingested={result['ingested']} "
          f"skipped={result['skipped']} total_docs={result['total_docs']}")


if __name__ == "__main__":
    main()
