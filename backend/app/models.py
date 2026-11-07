"""SQLAlchemy models for NEXUS."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="employee")
    department: Mapped[str] = mapped_column(String(64), nullable=False, default="general")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="upload")
    department: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    author: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    effective_date: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    access_policy: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    content_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, default=b"")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    idx: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, default=b"")
    embedding: Mapped[dict | list | None] = mapped_column(JSON, nullable=True, default=None)
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )
    user: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    action: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )
    user: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    action: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ChatHistory(Base):
    """Per-user chat turns. Answers stored are the masked, authorized-at-time
    text; history render re-checks authz and redacts revoked content."""

    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    query_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, default=b"")
    answer_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, default=b"")
    citations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ok")
    masked_pii: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )
