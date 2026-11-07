"""Security/audit read APIs.

- GET /security/events: admin/manager only. Event metadata only (type,
  user, timestamp, matched patterns); never restricted document content.
- GET /audit: admin only. Full audit trail (details are PII-masked at
  write time by the audit logger).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import get_current_user
from .database import get_session
from .models import AuditEvent, SecurityEvent, User

router = APIRouter(tags=["security"])

SECURITY_ROLES = {"admin", "manager"}
AUDIT_ROLES = {"admin"}


def _require_role(current: User, roles: set[str], what: str) -> None:
    if current.role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{what} requires role: {sorted(roles)}",
        )


def _event_to_dict(event: AuditEvent | SecurityEvent) -> dict:
    return {
        "id": event.id,
        "ts": event.ts.isoformat() if event.ts else "",
        "user": event.user,
        "action": event.action,
        "details": event.details or {},
    }


@router.get("/security/events")
def security_events(
    limit: int = 50,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> list[dict]:
    _require_role(current, SECURITY_ROLES, "security events")
    limit = max(1, min(int(limit or 50), 200))
    rows = db.scalars(
        select(SecurityEvent).order_by(SecurityEvent.id.desc()).limit(limit)
    ).all()
    return [_event_to_dict(r) for r in rows]


@router.get("/audit")
def audit_events(
    limit: int = 50,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> list[dict]:
    _require_role(current, AUDIT_ROLES, "audit log")
    limit = max(1, min(int(limit or 50), 200))
    rows = db.scalars(
        select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)
    ).all()
    return [_event_to_dict(r) for r in rows]
