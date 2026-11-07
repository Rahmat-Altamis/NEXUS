"""Documents router: upload/list/get/policy/delete, all authz-checked."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import log_audit, log_authz
from .auth import get_current_user
from .authz import authorized_doc_ids, check_access
from .crypto import decrypt_bytes
from .database import get_session
from .ingest import ingest_file
from .models import Document, User
from .vectorstore import delete_chunks_for_doc

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_ROLES = {"admin", "manager", "hr"}
POLICY_ROLES = {"admin", "manager"}
DELETE_ROLES = {"admin"}


class PolicyUpdate(BaseModel):
    access_policy: dict | None = None
    status: str | None = None


def _doc_to_dict(doc: Document) -> dict:
    return {
        "id": doc.id,
        "filename": doc.filename,
        "source_type": doc.source_type,
        "department": doc.department,
        "author": doc.author,
        "effective_date": doc.effective_date,
        "version": doc.version,
        "status": doc.status,
        "access_policy": doc.access_policy or {},
    }


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload(
    file: UploadFile,
    department: str = "general",
    author: str = "system",
    effective_date: str = "",
    current: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict:
    if current.role not in UPLOAD_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="upload requires admin/manager/hr")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty file")
    doc = ingest_file(
        db, file.filename or "upload", content,
        department=department, author=author or current.username,
        effective_date=effective_date,
    )
    log_audit(db, current.username, "document_upload", {"doc_id": doc.id, "filename": doc.filename})
    return _doc_to_dict(doc)


@router.get("")
def list_documents(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> list[dict]:
    ids = set(authorized_doc_ids(current, db))
    docs = db.scalars(select(Document).where(Document.id.in_(ids)) if ids else select(Document).where(False)).all()
    return [_doc_to_dict(d) for d in docs]


@router.get("/{doc_id}")
def get_document(
    doc_id: int,
    include_text: bool = False,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict:
    doc = db.scalar(select(Document).where(Document.id == doc_id))
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    allowed, reason = check_access(current, doc)
    log_authz(db, current.username, doc_id, allowed, reason)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"denied: {reason}")
    out = _doc_to_dict(doc)
    if include_text:
        try:
            out["text"] = decrypt_bytes(doc.content_encrypted).decode("utf-8")
        except Exception:
            out["text"] = ""
    return out


@router.put("/{doc_id}/policy")
def update_policy(
    doc_id: int,
    body: PolicyUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict:
    if current.role not in POLICY_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="policy change requires admin/manager")
    doc = db.scalar(select(Document).where(Document.id == doc_id))
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    if body.access_policy is not None:
        doc.access_policy = body.access_policy
    if body.status is not None:
        doc.status = body.status
    db.commit()
    db.refresh(doc)
    log_audit(db, current.username, "document_policy_update", {"doc_id": doc_id, "status": doc.status})
    return _doc_to_dict(doc)


@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict:
    if current.role not in DELETE_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="delete requires admin")
    doc = db.scalar(select(Document).where(Document.id == doc_id))
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    delete_chunks_for_doc(db, doc_id, commit=False)
    db.delete(doc)
    db.commit()
    log_audit(db, current.username, "document_delete", {"doc_id": doc_id})
    return {"deleted": doc_id}
