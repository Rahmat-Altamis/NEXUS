"""Audit + security event logging with PII masking."""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from .models import AuditEvent, SecurityEvent

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(\+?62|0)8\d{7,11}")
_NIK_RE = re.compile(r"\b\d{16}\b")


def mask_pii(text: str) -> str:
    text = _EMAIL_RE.sub("[email]", text)
    text = _PHONE_RE.sub("[phone]", text)
    text = _NIK_RE.sub("[nik]", text)
    return text


def _mask_value(value: Any) -> Any:
    if isinstance(value, str):
        return mask_pii(value)
    if isinstance(value, dict):
        return {k: _mask_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_mask_value(v) for v in value]
    return value


def _masked(details: dict) -> dict:
    # round-trip through json to ensure JSON-serializable
    return json.loads(json.dumps(_mask_value(details or {}), default=str))


def log_audit(db: Session, user: str, action: str, details: dict | None = None) -> AuditEvent:
    event = AuditEvent(user=user or "", action=action, details=_masked(details or {}))
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def log_security(db: Session, user: str, action: str, details: dict | None = None) -> SecurityEvent:
    event = SecurityEvent(user=user or "", action=action, details=_masked(details or {}))
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def log_query(
    db: Session,
    user: str,
    query: str,
    retrieved_doc_ids: list[int],
    response_status: str,
    authz_decision: str = "",
) -> AuditEvent:
    return log_audit(
        db,
        user,
        "query",
        {
            "query": query,
            "retrieved_doc_ids": retrieved_doc_ids,
            "response_status": response_status,
            "authz_decision": authz_decision,
        },
    )


def log_authz(
    db: Session, user: str, doc_id: int, allowed: bool, reason: str
) -> AuditEvent:
    return log_audit(
        db, user, "authz", {"doc_id": doc_id, "allowed": allowed, "reason": reason}
    )
