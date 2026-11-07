# NEXUS Architecture (final)

Synthetic demo only. No real PII. No secrets in code.

## System diagram (ASCII)

```
                    +--------------------+
                    |  React + Vite SPA  |
                    |  (frontend/)       |
                    |  Login Dashboard   |
                    |  Knowledge Assist. |
                    |  Security          |
                    +---------+----------+
                              |  JSON over HTTP (CORS: FRONTEND_URL)
                              |  Authorization: Bearer <JWT>
                              v
                    +---------+----------+
                    |  FastAPI backend   |
                    |  (backend/app/)    |
                    |                    |
  +----------+      |  /auth /documents  |      +-----------+
  |  SQLite  +------+  /chat /security   +------+  MockLLM  |
  |  (or PG) |  SQL |  /audit /stats     |  in- |  (default)|
  |  AES-GCM |<---> |  /me /health       |  proc|  or HTTP  |
  |  BLOBs   |      |                    |      |  LLM opt. |
  +----------+      |  agent.py pipeline +------+-----------+
                    |  (9 steps, see     |
                    |   below)           |
                    +---------+----------+
                              |
                    +---------+----------+
                    | In-memory vector   |
                    | store (LocalHash   |
                    | embeddings; Chroma |
                    | optional fallback) |
                    +--------------------+
```

## Request flow: POST /chat

```
1. classifier      salary/finance/PII intent detection
2. authz scope     authorized_doc_ids(user) from DB policies
3. retrieval       embed -> search ONLY authorized docs
                   (relevance gate: cosine >= 0.05 + token-overlap)
4. injection scan  query + passages, 12 patterns -> SecurityEvent
5. evidence check  conflict detection (conflicts.py), existence check
6. generate        LLM (MockLLM extractive, zero-overlap uncertainty)
7. PII mask        pre-mask passages + post-mask answer (HR + opt-in bypass)
8. citation check  drop invalid citations, verify readability
9. audit           log_query -> AuditEvent (PII-masked)
```

Statuses: `ok | refused (generic, no leak) | uncertain | conflict`.

## Component map

### Backend (`backend/app/`)

| Module | Responsibility |
|---|---|
| `main.py` | FastAPI entrypoint, CORS, routers, `/health`, `/me`, `/stats/summary` |
| `config.py` | Env settings, dev fallbacks with `RuntimeWarning` |
| `models.py` | `User, Document, Chunk, AuditEvent, SecurityEvent, ChatHistory` |
| `database.py` | Engine/session/`init_db`/`get_session` |
| `auth.py` | PBKDF2 passwords, JWT login, `get_current_user` from DB; `/auth/login`, `/auth/me` |
| `authz.py` | `check_access` (allow/deny+reason), `authorized_doc_ids`; admin bypass |
| `audit.py` | Query/authz/security logging, PII masking (email/phone/NIK) |
| `parsers.py` | PDF/DOCX/TXT/MD/CSV/JSON with graceful fallbacks + provenance |
| `chunking.py` | ~500-token windows, 50-token overlap, provenance |
| `embeddings.py` | `EmbeddingProvider` ABC, `LocalHashEmbedding` default, Chroma optional |
| `vectorstore.py` | `add_chunks`, `search` (authz filter BEFORE ranking), delete |
| `retrieval.py` | Embed -> authorized search -> dedupe -> passages (no vectors leaked) |
| `conflicts.py` | Keyword grouping, numeric/date compare, announcement>SOP-if-newer |
| `pii.py` | Mask NIK/phone/email/address unless HR + opt-in |
| `injection.py` | 12-pattern detect, `scan_and_log`, neutralize |
| `ingest.py` | Parse -> chunk -> AES encrypt -> embed -> index; `reindex_document` |
| `documents.py` | `/documents` CRUD + policy (role-gated) |
| `llm.py` | `LLMProvider` ABC, `MockLLM` default, `OptionalHttpLLM` (env-gated) |
| `agent.py` | 9-step pipeline (above) |
| `chat.py` | `POST /chat`, `GET /chat/history` (own-only, revoke-redacted) |
| `security.py` | `GET /security/events` (admin/manager), `GET /audit` (admin) |
| `crypto.py` | AES-256-GCM field encryption, unique nonce, tamper -> `ValueError` |

### Frontend (`frontend/src/`)

| Path | Responsibility |
|---|---|
| `lib/api.ts` | Typed client, `VITE_API_URL`, Bearer [REDACTED] |
| `lib/i18n.ts` | ID/EN strings |
| `lib/auth.tsx` | Login/token/`/me`/role gates, 5 demo buttons |
| `components/ui.tsx` | Shared UI primitives |
| `pages/Login.tsx` | Login + demo accounts |
| `pages/Dashboard.tsx` | Stats cards, visible docs, recent queries, sec events |
| `pages/Knowledge.tsx` | List/preview/upload/policy/revoke/delete (role-gated) |
| `pages/Assistant.tsx` | Chat + citations + conflicts + history |
| `pages/Security.tsx` | Event feeds, metadata-only rendering |
| `App.tsx` | Tab navigation |

### Data / scripts / tests

| Path | Responsibility |
|---|---|
| `data/synthetic/` | 24 docs + 10 chats + 4 task files; see `permission_matrix.md` |
| `scripts/seed_users.py` | 5 demo users + 2 test docs (early-phase seed) |
| `scripts/seed_data.py` | Full 38-file dataset seed (idempotent) |
| `scripts/run_all.sh` | Install -> seed -> pytest -> uvicorn smoke |
| `tests/` | `test_01..test_10` (27 tests), isolated tmp DB |

## Key decisions (kept from Phase 1)

- SQLite default, Postgres-portable (`DATABASE_URL`), no SQLite-specific SQL.
- Local hash embeddings default; Chroma optional with graceful fallback.
- Mock LLM default; HTTP LLM opt-in via `LLM_API_URL`, falls back to mock.
- Plain JSON chat transport (not SSE): citation-integrity + PII masking must
  complete on the full answer before anything is sent.
- CORS allowlist from `FRONTEND_URL` (default `http://localhost:5173`).
