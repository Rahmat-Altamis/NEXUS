# NEXUS Threat Model

Synthetic demo only. No real PII. Scope: the FastAPI backend, the React SPA,
the SQLite/Postgres store, and the synthetic dataset.

## Assets

| # | Asset | Why it matters |
|---|---|---|
| A1 | Document/chunk plaintext (AES-GCM columns) | Confidential knowledge per policy |
| A2 | `ENCRYPTION_KEY` / `JWT_SECRET` | Total confidentiality + auth integrity |
| A3 | Chat history (encrypted queries/answers) | May repeat restricted content |
| A4 | Access policies + audit/security logs | Integrity of who-saw-what evidence |
| A5 | Demo credentials / JWTs | Session impersonation |
| A6 | PII in dataset (fake NIK/phones/emails) | Masking-behavior correctness |

## Threats + mitigations

| # | Threat | Mitigation (implemented) |
|---|---|---|
| T1 | Unauthorized read via retrieval (cross-dept leak) | Authz-before-retrieval: `authorized_doc_ids` filter before ranking; per-request policy re-read |
| T2 | Unauthorized read via direct URL (`GET /documents/{id}`) | `check_access_by_id` fresh-load; 403 on deny |
| T3 | Stale access after policy revoke | No cached grants; history re-check + redact revoked turns |
| T4 | Existence oracle (refusal wording leaks doc presence) | Generic refused message, no doc signal, ID+EN |
| T5 | DB file theft / offline read | AES-256-GCM on content columns; unique nonce; tamper -> error |
| T6 | Prompt injection in docs or chat | 12-pattern detect, `scan_and_log` -> SecurityEvent, neutralize; extractive MockLLM |
| T7 | PII exfiltration via answers/logs | Pre-mask passages + post-mask answer; audit masking; unmask only HR + explicit opt-in |
| T8 | Privilege escalation (client role claims) | Roles/departments always from DB row; upload/policy/delete role-gated server-side |
| T9 | Token forgery / weak passwords | HS256 JWT with server secret; PBKDF2 200k + salt |
| T10 | Citation fabrication / vector leak | Citation-integrity check drops invalid cites; vectors never leave the API |
| T11 | Secrets committed to repo | `.env.example` placeholders only; `.gitignore` covers `.env`, `*.db`, `node_modules` |

## Residual risks (accepted for MVP)

- R1: No TLS in-app — deploy behind HTTPS or tokens/content traverse plaintext.
- R2: JWT in `localStorage` — any frontend XSS steals sessions; no CSP headers.
- R3: No rate limiting / lockout — demo passwords are brute-forceable.
- R4: Heuristic injection filter — a novel phrasing can bypass the 12 patterns;
  residual impact is bounded by extractive generation + authz scoping.
- R5: Single-key encryption, no rotation/escrow — key loss = data loss; key
  leak = full historical decryption.
- R6: Audit log is not tamper-evident — a DB writer can alter history.
- R7: Metadata (filenames, policies, counts) is plaintext in the DB.
- R8: HTTP-LLM mode (`LLM_API_URL`) sends authorized passages to an external
  endpoint — operator must trust that endpoint.
