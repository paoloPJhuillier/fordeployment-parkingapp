#!/usr/bin/env bash
# ----------------------------------------------------------------------------
# deploy.sh — Build images and bring the parking app stack up.
#
# Usage:
#   ./deploy/deploy.sh              # default profile (mongo + backend + frontend)
#   ./deploy/deploy.sh couchbase    # backend + frontend pointed at Capella (no local mongo)
#   FORCE_REBUILD=1 ./deploy/deploy.sh   # --no-cache rebuild
#
# Reads .env at the repo root. If .env is missing, copies .env.example and
# bails out so the operator can fill in secrets first.
# ----------------------------------------------------------------------------
set -Eeuo pipefail

cd "$(dirname "$0")/.."

PROFILE="${1:-default}"
FORCE_REBUILD="${FORCE_REBUILD:-0}"

# ---------- 1. Pre-flight checks --------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed or not on PATH." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: 'docker compose' plugin not available (need Docker Engine 20.10+ with compose v2)." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp .env.example .env
    echo "[deploy] No .env found — copied .env.example to .env."
    echo "[deploy] Edit .env and set JWT_SECRET, FIRST_ADMIN_PASSWORD, etc., then re-run."
    exit 1
  else
    echo "ERROR: .env and .env.example both missing." >&2
    exit 1
  fi
fi

# Lightweight production-secret sanity checks.
if grep -qE '^JWT_SECRET=changeme' .env; then
  echo "ERROR: JWT_SECRET is still the placeholder. Generate one with: openssl rand -hex 64" >&2
  exit 1
fi
# Production default is Couchbase: ensure cluster vars are set.
if [[ "$PROFILE" != "dev-mongo" ]]; then
  for v in COUCHBASE_CONNECTION_STRING COUCHBASE_BUCKET COUCHBASE_USERNAME COUCHBASE_PASSWORD; do
    if ! grep -qE "^${v}=.+\$" .env; then
      echo "ERROR: $v is empty in .env (required for the default Couchbase profile). Use 'deploy.sh dev-mongo' if you want the bundled MongoDB." >&2
      exit 1
    fi
  done
fi

# ---------- 2. Build & start -------------------------------------------------
BUILD_FLAGS="--build"
[[ "$FORCE_REBUILD" == "1" ]] && BUILD_FLAGS="--build --no-cache"

if [[ "$PROFILE" == "dev-mongo" ]]; then
  echo "[deploy] Profile: dev-mongo  (backend + frontend + bundled MongoDB)"
  DB_TYPE=mongodb docker compose --profile dev-mongo up -d $BUILD_FLAGS
else
  echo "[deploy] Profile: default  (backend + frontend, external Couchbase)"
  docker compose up -d $BUILD_FLAGS
fi

# ---------- 3. Wait for healthy ---------------------------------------------
echo "[deploy] Waiting for containers to report healthy (up to 120s)…"
deadline=$(( $(date +%s) + 120 ))
while [[ $(date +%s) -lt $deadline ]]; do
  unhealthy=$(docker compose ps --format json 2>/dev/null \
    | python3 -c "
import sys, json
docs = []
raw = sys.stdin.read().strip()
if raw.startswith('['):
    docs = json.loads(raw)
else:
    for line in raw.splitlines():
        if line.strip(): docs.append(json.loads(line))
bad = [d['Service'] for d in docs if d.get('Health') and d['Health'] not in ('healthy','')]
print(','.join(bad))
" 2>/dev/null || echo "ERR")
  if [[ -z "$unhealthy" ]]; then
    echo "[deploy] All services healthy."
    break
  fi
  sleep 3
done

# ---------- 4. Smoke test ---------------------------------------------------
"$(dirname "$0")/health.sh" || {
  echo "[deploy] Smoke test failed. Check logs with: ./deploy/logs.sh" >&2
  exit 1
}

echo
echo "[deploy] Done."
echo "[deploy] Frontend:  http://localhost:${FRONTEND_PORT:-3000}"
echo "[deploy] Backend:   http://localhost:8001  (bound to 127.0.0.1 only)"
echo "[deploy] Logs:      ./deploy/logs.sh [backend|frontend|mongo]"
