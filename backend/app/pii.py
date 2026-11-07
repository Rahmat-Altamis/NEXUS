"""PII masking for Indonesian documents."""

from __future__ import annotations

import re

_NIK_RE = re.compile(r"\b\d{16}\b")
_PHONE_RE = re.compile(r"(?:\+62|62|0)8\d{6,12}\b|(?:\+62|62|0)\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}\b")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_ADDRESS_RE = re.compile(
    r"\b(Jl\.?|Jalan|Gedung|Komp(?:lek)?s?|Perumahan|RT\s?\d+\s?/?\s?RW\s?\d+|Kel\.?|Kec\.?|Kota|Kabupaten|Provinsi|Kode\s?Pos\s?\d{5})[^\n,;]{0,80}",
    re.IGNORECASE,
)


def mask(text: str, authorized: bool = False) -> str:
    """Mask NIK, phone, email and address fragments unless authorized."""
    if authorized or not text:
        return text
    text = _NIK_RE.sub("[NIK]", text)
    text = _PHONE_RE.sub("[PHONE]", text)
    text = _EMAIL_RE.sub("[EMAIL]", text)
    text = _ADDRESS_RE.sub("[ADDRESS]", text)
    return text
