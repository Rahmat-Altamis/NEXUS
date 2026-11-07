# Deployment — NEXUS on Ubuntu VPS (nginx + systemd)

Live instance: `http://[2a01:4f9:3080:3192::1961]/` (IPv6, HTTP).
Same-origin setup: nginx serves the SPA and proxies `/api/` to uvicorn,
so no CORS or extra firewall ports are needed. Build the frontend with
`VITE_API_URL=/api`.

## Layout on the server

| Path | Content |
|---|---|
| `/opt/nexus/` | `backend/`, `scripts/`, `data/`, `.env` (0600), `.venv/`, `nexus.db` (0600) |
| `/var/www/nexus/` | Built frontend (`dist/` contents) |
| `/etc/systemd/system/nexus.service` | Backend service (uvicorn on 127.0.0.1:8000) |
| `/etc/nginx/sites-enabled/nexus` | SPA + `/api/` reverse proxy |

## Initial deploy (from this repo, SSH key access to the VPS)

```bash
# 1. venv + deps
ssh root@VPS 'mkdir -p /opt/nexus && python3 -m venv /opt/nexus/.venv \
  && /opt/nexus/.venv/bin/pip install fastapi uvicorn pydantic sqlalchemy \
  python-multipart pyjwt cryptography httpx'

# 2. ship code (exactly what is committed)
git archive HEAD backend scripts data .env.example | ssh root@VPS 'tar -x -C /opt/nexus'

# 3. secrets + seed (run ON the server so keys never transit in shell history)
ssh root@VPS
python3 -c "import base64,os; print(base64.b64encode(os.urandom(32)).decode())"  # ENCRYPTION_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(48))"                   # JWT_SECRET
# write /opt/nexus/.env (mode 600):
#   DATABASE_URL=sqlite:////opt/nexus/nexus.db
#   ENCRYPTION_KEY=<...>
#   JWT_SECRET=<...>
set -a; . /opt/nexus/.env; set +a
/opt/nexus/.venv/bin/python scripts/seed_users.py
/opt/nexus/.venv/bin/python scripts/seed_data.py
chmod 600 /opt/nexus/nexus.db

# 4. systemd service (see /etc/systemd/system/nexus.service on the server)
systemctl daemon-reload && systemctl enable --now nexus

# 5. frontend
cd frontend && VITE_API_URL=/api npm run build
scp -r dist root@VPS:/tmp/nexus_dist
# on server: rm -rf /var/www/nexus && mv /tmp/nexus_dist /var/www/nexus

# 6. nginx site (SPA + /api/ proxy), then: nginx -t && systemctl reload nginx
```

## Redeploy after a code change

```bash
git archive HEAD backend scripts data | ssh root@VPS 'tar -x -C /opt/nexus'
ssh root@VPS systemctl restart nexus
cd frontend && VITE_API_URL=/api npm run build   # only if frontend changed
scp -r dist root@VPS:/tmp/nexus_dist && ssh root@VPS 'rm -rf /var/www/nexus && mv /tmp/nexus_dist /var/www/nexus'
```

Re-seeding wipes Q&A history but keeps code-owned data; the scripts are
idempotent (already-ingested filenames are skipped).

## Notes / limitations of this setup

- HTTP only. For HTTPS, point DNS at this VPS and add certbot (`certbot
  --nginx`); `hackclub.app` currently resolves to a different (Caddy) host.
- SQLite at `/opt/nexus/nexus.db`; for Postgres set `DATABASE_URL` in
  `/opt/nexus/.env` and restart.
- Demo credentials are seeded (`siti/hana/budi/dewi/agus`, password
  `<name>-demo-pass`); rotate or disable before any real use.
- Logs: `journalctl -u nexus -f`.
