"""Field-level encryption: REAL AES-256-GCM via the `cryptography` lib.

- Unique 96-bit nonce per operation (os.urandom).
- Tag is combined with ciphertext (AESGCM appends the 16-byte tag).
- Tampered payloads raise ValueError.
- Never log plaintext or keys.
"""

from __future__ import annotations

import base64
import hashlib
import os
from typing import Union

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import get_encryption_key

_NONCE_BYTES = 12
_KEY_BYTES = 32

_key_cache: bytes | None = None


def _derive_key(raw: str) -> bytes:
    """Normalize user-supplied key material to 32 bytes.

    Accepts: Fernet-style urlsafe-b64 (32 bytes), standard b64, hex, or an
    arbitrary passphrase (SHA-256 derived). Passphrase derivation is a dev
    convenience; production should supply 32 raw random bytes (b64).
    """
    text = raw.strip()
    # urlsafe b64 (Fernet keys)
    try:
        padded = text + "=" * (-len(text) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
        if len(decoded) == _KEY_BYTES:
            return decoded
    except Exception:
        pass
    # standard b64
    try:
        padded = text + "=" * (-len(text) % 4)
        decoded = base64.b64decode(padded.encode("ascii"))
        if len(decoded) == _KEY_BYTES:
            return decoded
    except Exception:
        pass
    # hex
    try:
        decoded = bytes.fromhex(text)
        if len(decoded) == _KEY_BYTES:
            return decoded
    except Exception:
        pass
    # raw 32-byte string
    raw_bytes = text.encode("utf-8")
    if len(raw_bytes) == _KEY_BYTES:
        return raw_bytes
    # fallback: derive (dev passphrases)
    return hashlib.sha256(raw_bytes).digest()


def _get_key() -> bytes:
    global _key_cache
    if _key_cache is None:
        _key_cache = _derive_key(get_encryption_key())
    return _key_cache


def _b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64d(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))


def encrypt(plaintext: Union[str, bytes]) -> dict:
    """Encrypt plaintext. Returns {"nonce": b64, "ciphertext": b64(tag combined)}."""
    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")
    nonce = os.urandom(_NONCE_BYTES)
    ct_and_tag = AESGCM(_get_key()).encrypt(nonce, plaintext, None)
    return {"nonce": _b64e(nonce), "ciphertext": _b64e(ct_and_tag)}


def decrypt(payload: dict) -> str:
    """Decrypt a payload from encrypt(). Raises ValueError on tamper/format errors."""
    try:
        nonce = _b64d(payload["nonce"])
        ct_and_tag = _b64d(payload["ciphertext"])
    except Exception as exc:
        raise ValueError("invalid encrypted payload format") from exc
    try:
        plaintext = AESGCM(_get_key()).decrypt(nonce, ct_and_tag, None)
    except InvalidTag as exc:
        raise ValueError("decryption failed: tampered or wrong key") from exc
    return plaintext.decode("utf-8")


def encrypt_bytes(plaintext: bytes) -> bytes:
    """Compact binary form: nonce(12) || ciphertext+tag. For BLOB columns."""
    nonce = os.urandom(_NONCE_BYTES)
    return nonce + AESGCM(_get_key()).encrypt(nonce, plaintext, None)


def decrypt_bytes(blob: bytes) -> bytes:
    """Inverse of encrypt_bytes. Raises ValueError on tamper/format errors."""
    if len(blob) < _NONCE_BYTES + 16:
        raise ValueError("invalid encrypted blob")
    nonce, ct_and_tag = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
    try:
        return AESGCM(_get_key()).decrypt(nonce, ct_and_tag, None)
    except InvalidTag as exc:
        raise ValueError("decryption failed: tampered or wrong key") from exc
