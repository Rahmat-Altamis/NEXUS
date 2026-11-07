"""Chat router: POST /chat (Q/A) + GET /chat/history (own only).

Transport choice: plain JSON request/response. SSE streaming was considered
but deferred -- answers are short extractive summaries, so a single JSON
payload keeps citation-integrity and PII-masking checks atomic (they run on
the complete answer before anything is sent). Add SSE later by streaming
only the final verified answer text.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import agent as agent_mod
from .audit import mask_pii
from .auth import get_current_user
from .crypto import decrypt_bytes, encrypt_bytes
from .database import get_session
from .models import ChatHistory, User

router = APIRouter(prefix="/chat", tags=["chat"])

_REDACTED = "[redacted: access revoked]"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    lang: str = Field(default="id", max_length=8)
    allow_pii: bool = False


class ChatResponse(BaseModel):
    answer: str
    citations: list[dict] = []
    status: str = "ok"
    warnings: list[str] = []
    masked_pii: bool = False


class HistoryItem(BaseModel):
    id: int
    query: str
    answer: str
    citations: list[dict] = []
    status: str
    redacted: bool = False


def _store_turn(
    db: Session, username: str, query: str, result: dict
) -> ChatHistory:
    row = ChatHistory(
        user=username,
        query_encrypted=encrypt_bytes(mask_pii(query).encode("utf-8")),
        answer_encrypted=encrypt_bytes((result.get("answer") or "").encode("utf-8")),
        citations=result.get("citations") or [],
        status=result.get("status") or "ok",
        masked_pii=1 if result.get("masked_pii") else 0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _render_row(db: Session, user: User, row: ChatHistory) -> HistoryItem:
    """Render one history row, re-checking authz to block revoked content."""
    citations = row.citations or []
    visible = agent_mod.history_answer_visible(db, user, citations)
    try:
        query = decrypt_bytes(row.query_encrypted).decode("utf-8")
    except Exception:
        query = ""
    if not visible:
        return HistoryItem(
            id=row.id, query=query, answer=_REDACTED,
            citations=[], status=row.status, redacted=True,
        )
    try:
        answer = decrypt_bytes(row.answer_encrypted).decode("utf-8")
    except Exception:
        answer = _REDACTED
        return HistoryItem(
            id=row.id, query=query, answer=answer,
            citations=[], status=row.status, redacted=True,
        )
    return HistoryItem(
        id=row.id, query=query, answer=answer,
        citations=citations, status=row.status, redacted=False,
    )


@router.post("", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> ChatResponse:
    message = (body.message or "").strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="empty message"
        )
    result = agent_mod.answer_query(
        db, current, message, lang=body.lang, allow_pii=body.allow_pii
    )
    _store_turn(db, current.username, message, result)
    return ChatResponse(
        answer=result["answer"],
        citations=result["citations"],
        status=result["status"],
        warnings=result["warnings"],
        masked_pii=result["masked_pii"],
    )


@router.get("/history", response_model=list[HistoryItem])
def history(
    limit: int = 20,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> list[HistoryItem]:
    limit = max(1, min(int(limit or 20), 100))
    rows = db.scalars(
        select(ChatHistory)
        .where(ChatHistory.user == current.username)
        .order_by(ChatHistory.id.desc())
        .limit(limit)
    ).all()
    return [_render_row(db, current, r) for r in rows]
