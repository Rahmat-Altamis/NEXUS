# NEXUS — Permission-Aware Enterprise Knowledge Assistant

Product vision: a company knowledge assistant where **authorization comes
before retrieval**. Every answer is grounded only in documents the asker is
allowed to read, with `[doc:chunk]` citations, conflict surfacing, PII
masking, and prompt-injection defenses — all audited. Synthetic demo data
only (Nusantara Digital Group, fictitious). No secrets in code. No real PII.

## Quickstart

Backend (from repo root):

```bash
pip install -r backend/requirements.txt
cp .env.example .env        # then set ENCRYPTION_KEY (see below)
python scripts/seed_data.py # 5 users + 38 synthetic files (idempotent)
uvicorn app.main:app --app-dir backend --reload
curl localhost:8000/health
```

Generate a key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Frontend (from repo root):

```bash
cd frontend
npm install
npm run dev     # dev server (default http://localhost:5173)
npm run build   # production build -> dist/
```

One-shot (install -> seed -> test -> smoke): `bash scripts/run_all.sh`.

Tests: `python -m pytest tests -q` (isolated tmp DB, 27 tests).

## Demo accounts

| Username | Password | Role | Department |
|---|---|---|---|
| siti | siti-demo-pass | employee | engineering |
| hana | hana-demo-pass | hr | hr |
| budi | budi-demo-pass | manager | engineering |
| dewi | dewi-demo-pass | finance | finance |
| agus | agus-demo-pass | admin | it (bypasses all policies) |

## Permission matrix (summary)

| Level | Who can read |
|---|---|
| PUBLIC | everyone |
| HR_ONLY | hana, agus |
| FIN_ONLY | dewi, agus |
| MGR_ONLY | budi, agus |
| GARUDA (`allowed_users: siti, budi`) | siti, budi, agus |
| ENG_DEPT (`allowed_departments: engineering`) | siti, budi, agus |

Full per-file map: [data/synthetic/permission_matrix.md](data/synthetic/permission_matrix.md).

## API overview

| Method + path | Auth | Description |
|---|---|---|
| `GET /health` | no | Liveness probe |
| `POST /auth/login` | no | `{username, password}` -> JWT |
| `GET /auth/me`, `GET /me` | Bearer | Current user |
| `GET /stats/summary` | no | Entity counts |
| `POST /documents/upload` | admin/manager/hr | Upload + ingest |
| `GET /documents` | Bearer | List authorized-only |
| `GET /documents/{id}[?include_text=true]` | authz-checked | Metadata (+ text) |
| `PUT /documents/{id}/policy` | admin/manager | Re-policy (revoke = immediate) |
| `DELETE /documents/{id}` | admin | Delete |
| `POST /chat` | Bearer | `{message, lang, allow_pii}` -> `{answer, citations, status, warnings, masked_pii}` (`ok\|refused\|uncertain\|conflict`) |
| `GET /chat/history` | Bearer | Own turns only; revoked redacted |
| `GET /security/events` | admin/manager | Injection/authz decision feed |
| `GET /audit` | admin | Query audit log |

## Limitations

- Mock extractive LLM by default; Meta Model API (`muse-spark-1.3`) via `LLM_PROVIDER=meta` + `META_API_KEY`, or custom HTTP LLM via `LLM_API_URL`. Both fall back to mock on any error.
- Local hash embeddings default; Chroma optional.
- No TLS, rate limiting, MFA, key rotation/escrow, or tamper-evident audit.
- JWT in `localStorage`; heuristic (12-pattern) injection filter.
- See [docs/security.md](docs/security.md) ("What is NOT covered") and
  [docs/threat-model.md](docs/threat-model.md) (residual risks).

## Repo structure

```
nexus/
  backend/app/        FastAPI service (auth, authz, ingest, retrieval, agent, chat)
  backend/requirements.txt
  frontend/src/       React + TS + Vite + Tailwind (Login, Dashboard, Knowledge, Assistant, Security)
  data/synthetic/     docs/ chats/ tasks/ + permission_matrix.md
  tests/              test_01..test_10 + conftest.py (isolated DB)
  scripts/            seed_users.py, seed_data.py, run_all.sh
  docs/               architecture.md, security.md, threat-model.md,
                      accountability.md, testing-report.md
  .env.example  .gitignore  README.md
```

Further reading: [docs/architecture.md](docs/architecture.md) ·
[docs/security.md](docs/security.md) ·
[docs/threat-model.md](docs/threat-model.md) ·
[docs/accountability.md](docs/accountability.md) ·
[docs/testing-report.md](docs/testing-report.md)
