"""test_09: encryption — AES-256-GCM at rest; tamper rejected; nonce unique."""

import pytest
from sqlalchemy import select


def test_stored_content_is_encrypted(seeded_ids):
    from app.crypto import decrypt_bytes
    from app.database import SessionLocal
    from app.models import Chunk, Document

    db = SessionLocal()
    try:
        doc = db.scalar(select(Document).where(Document.filename == "it-security-policy.md"))
        assert doc is not None
        assert b"reset password" not in doc.content_encrypted
        assert "reset password" in decrypt_bytes(doc.content_encrypted).decode()

        chunk = db.scalar(select(Chunk).where(Chunk.doc_id == doc.id))
        assert chunk is not None
        assert b"reset password" not in chunk.text_encrypted
        assert "reset password" in decrypt_bytes(chunk.text_encrypted).decode()
    finally:
        db.close()


def test_tampered_blob_rejected(seeded_ids):
    from app.crypto import decrypt_bytes
    from app.database import SessionLocal
    from app.models import Document

    db = SessionLocal()
    try:
        doc = db.scalar(select(Document).limit(1))
        tampered = bytearray(doc.content_encrypted)
        tampered[-1] ^= 0xFF
        with pytest.raises(ValueError):
            decrypt_bytes(bytes(tampered))
    finally:
        db.close()


def test_encrypt_nonce_unique_and_roundtrip():
    from app.crypto import decrypt, encrypt

    first, second = encrypt("nexus probe"), encrypt("nexus probe")
    assert first["nonce"] != second["nonce"]
    assert first["ciphertext"] != second["ciphertext"]
    assert decrypt(first) == "nexus probe"

    bad = dict(first)
    bad["ciphertext"] = bad["ciphertext"][:-4] + ("AAAA" if not bad["ciphertext"].endswith("AAAA") else "BBBB")
    with pytest.raises(ValueError):
        decrypt(bad)
