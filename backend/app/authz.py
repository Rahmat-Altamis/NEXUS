"""RBAC + resource-level authorization.

- Explicit allow/deny with reasons.
- Revocation is immediate: policy is always loaded fresh from the DB
  (no caching); check_access_by_id re-reads the row per call.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Document, User

DENY = (False, "")
ALLOW = (True, "")


def check_access(user: User, doc: Document) -> tuple[bool, str]:
    """Evaluate access for an already-loaded doc. Returns (allowed, reason)."""
    # Admin bypass (explicit allow).
    if user.role == "admin":
        return True, "allow:admin"

    # Revoked/archived docs are denied to non-admins.
    if (doc.status or "").lower() in {"revoked", "deleted", "quarantined"}:
        return False, f"deny:status={doc.status}"

    policy: dict = doc.access_policy or {}

    denied_users = set(policy.get("denied_users", []) or [])
    if user.username in denied_users:
        return False, "deny:user-blocked"

    denied_roles = set(policy.get("denied_roles", []) or [])
    if user.role in denied_roles:
        return False, "deny:role-blocked"

    allowed_users = policy.get("allowed_users")
    if allowed_users is not None and user.username not in set(allowed_users):
        return False, "deny:not-in-allowed-users"
    if allowed_users is not None and user.username in set(allowed_users):
        return True, "allow:user-listed"

    allowed_roles = policy.get("allowed_roles")
    if allowed_roles is not None:
        if user.role in set(allowed_roles):
            return True, "allow:role-listed"
        return False, "deny:role-not-listed"

    allowed_departments = policy.get("allowed_departments")
    if allowed_departments is not None:
        if user.department in set(allowed_departments):
            return True, "allow:department-listed"
        return False, "deny:department-not-listed"

    # Default: same-department docs are readable; cross-department denied
    # for non-managers (managers may read across departments).
    if doc.department and user.department == doc.department:
        return True, "allow:same-department"
    if user.role == "manager":
        return True, "allow:manager-cross-department"
    return False, "deny:cross-department"


def check_access_by_id(db: Session, user: User, doc_id: int) -> tuple[bool, str]:
    """Fresh-policy check: reloads the doc row from the DB on every call."""
    db.expire_all()
    doc = db.scalar(select(Document).where(Document.id == doc_id))
    if doc is None:
        return False, "deny:doc-not-found"
    return check_access(user, doc)


def authorized_doc_ids(user: User, db: Session) -> list[int]:
    """Doc ids the user may retrieve. Used to scope retrieval queries."""
    db.expire_all()
    docs = db.scalars(select(Document)).all()
    return [d.id for d in docs if check_access(user, d)[0]]
