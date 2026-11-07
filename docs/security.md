# NEXUS Security

Synthetic demo only. No real PII. No secrets in code.

## 1. Authorization before retrieval (core invariant)

Every read path filters by authorization **before** ranking or generation:

- `authz.authorized_doc_ids(user)` resolves the readable doc set from live DB
  policies (`allowed_roles`, `allowed_departments`, `allowed_users`; admin
  bypass). Roles/departments always come from the DB row — never from client
  claims.
- `vectorstore.search(..., authorized_doc_ids=...)` applies the filter before
  similarity ranking, so unauthorized chunks never influence scores or answers.
- Revocation is immediate: policies are re-read per request (no cached grants).
  `GET /chat/history` re-checks authz per cited doc and redacts revoked turns.
- Refusals are generic ("maaf, saya tidak menemukan informasi...") with no
  doc-existence signal, in the requested language (ID/EN).
- Direct object access is also guarded: `GET /documents/{id}` returns 403 for
  cross-policy reads.

## 2. AES-256-GCM boundaries

- Algorithm: AES-256-GCM via the `cryptography` library (`crypto.py`).
- Key normalization: Fernet-style urlsafe-b64 / standard b64 / hex / raw
  32 bytes used directly; anything else is SHA-256-derived (dev convenience).
- Nonce: unique 96-bit `os.urandom` per encryption; tag bundled with
  ciphertext; tampered payloads raise `ValueError` (never partial plaintext).
- Encrypted at rest: `Document.content_encrypted`, `Chunk.text_encrypted`,
  `ChatHistory` query/answer. Embeddings/vectors are internal-only and never
  returned by any API.
- Never logged: plaintext, keys, or decrypted chat content. Audit logs are
  PII-masked (email/phone/NIK).

## 3. Key management, rotation, recovery

- Keys come only from env (`ENCRYPTION_KEY`, `JWT_SECRET`). Missing
  `ENCRYPTION_KEY` (or the `REPLACE_WITH_...` placeholder) triggers a
  `RuntimeWarning` and an insecure dev fallback — production must set a real
  32-byte key.
- Generate: `python -c "from cryptography.fernet import Fernet;
  print(Fernet.generate_key().decode())"`.
- Rotation: this MVP has **no automated rotation**. To rotate, re-encrypt the
  DB offline (decrypt with old key, encrypt with new key) during a maintenance
  window. There is no multi-key support.
- Recovery: there is **no key escrow or recovery**. Losing `ENCRYPTION_KEY`
  means encrypted columns are permanently unreadable. Back the key up in a
  secrets manager (out of scope for this repo).
- JWT: HS256, `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60). Passwords are
  PBKDF2-HMAC-SHA256 (200k iterations) with per-user salt.

## 4. Transport

- JSON over HTTP; Bearer [REDACTED] (`Authorization: Bearer <token>`).
- CORS allowlist from `FRONTEND_URL` (comma-separated allowed).
- TLS is **not** configured in-app: run behind an HTTPS reverse proxy in any
  non-local deployment. Tokens in `localStorage` (frontend) are XSS-readable
  by design of this demo — a production build should use httpOnly cookies.

## 5. What is NOT covered

- No TLS termination, no rate limiting, no account lockout / brute-force
  protection (demo passwords are weak by design).
- No automated key rotation, escrow, or multi-key support.
- No row-level DB encryption beyond the crypto columns; metadata (filenames,
  policies, audit counts) is plaintext.
- Prompt-injection defenses are heuristic (12 patterns + neutralize), not a
  guarantee; the LLM is extractive-by-default which limits but does not remove
  the risk.
- No SSO/MFA, no fine-grained per-chunk policies, no data-loss-prevention on
  exports, no signed audit trail (tamper-evident logging is future work).
- Frontend stores the JWT in `localStorage` (XSS-readable); no CSP headers set.
