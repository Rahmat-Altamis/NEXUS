# NEXUS Frontend

React + TypeScript + Vite + Tailwind CSS console for the NEXUS secure
enterprise knowledge assistant. Dark ops-console theme, responsive, bilingual
(ID/EN).

## Prerequisites

- Node.js 18+ and npm
- NEXUS backend running (default `http://localhost:8000`)

## Setup

```bash
cd nexus/frontend
cp .env.example .env        # optional; defaults to http://localhost:8000
npm install
npm run dev                 # http://localhost:5173
```

Production build:

```bash
npm run build    # type-checks (tsc) + emits dist/
npm run preview  # serve the production build locally
```

## Configuration

| Variable       | Default                 | Meaning              |
|----------------|-------------------------|----------------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend base URL     |

The backend must allow this origin via its `FRONTEND_URL` env var
(default `http://localhost:5173`).

## Demo logins

One-click buttons on the login screen (password = `<user>-demo-pass`):

| User | Role     | Sees                                     |
|------|----------|------------------------------------------|
| agus | admin    | everything + audit trail + delete docs   |
| budi | manager  | security events + policy edit + upload   |
| hana | hr       | upload + unmasked PII with opt-in toggle |
| dewi | finance  | finance-scoped answers                   |
| siti | employee | own-department docs only                 |

## Tabs

- **Dashboard** — stats from `/stats/summary`, visible docs, recent queries,
  latest security events (manager+).
- **Knowledge** — list/preview/upload/policy/revoke/delete docs, role-gated.
  The UI hides unauthorized actions, but the backend is the source of truth
  (every call is authz-checked server-side).
- **AI Assistant** — chat with ID/EN toggle, clickable `[doc:chunk]` citation
  chips opening a passage-preview modal, conflict/uncertainty/refusal styling,
  PII-mask badges, per-user history.
- **Security** (manager/admin) — access decisions, denials, injection
  detections, policy changes, audit trail (admin only). Event metadata only;
  restricted content is never rendered.

## Scripts

- `npm run dev` — Vite dev server
- `npm run build` — `tsc -b && vite build`
- `npm run preview` — preview `dist/`
- `npm run lint` — oxlint
