#!/usr/bin/env bash
# NEXUS one-shot: backend install + seed + test + smoke check.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export DATABASE_URL="sqlite:///$ROOT/nexus.db"

echo "==> install backend deps"
if ! python -m pip install -r backend/requirements.txt; then
  echo "pip install blocked here; verifying required imports instead"
  python -c "import fastapi, sqlalchemy, jwt, cryptography, pytest, httpx; print('deps present')"
fi

echo "==> seed users + synthetic dataset"
python scripts/seed_data.py

echo "==> run test suite"
python -m pytest tests -v

echo "==> smoke check (boot uvicorn, probe endpoints)"
python - <<'EOF'
import json, subprocess, sys, time, urllib.request

proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8131"],
    cwd="backend", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
try:
    health = None
    for _ in range(50):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8131/health", timeout=2) as r:
                health = json.load(r)
            break
        except Exception:
            time.sleep(0.2)
    assert health and health.get("status") == "ok", f"bad /health: {health}"
    print("smoke /health:", health)
    with urllib.request.urlopen("http://127.0.0.1:8131/stats/summary", timeout=5) as r:
        print("smoke /stats/summary:", json.load(r))
    print("smoke OK")
finally:
    proc.terminate()
    proc.wait(timeout=10)
EOF
