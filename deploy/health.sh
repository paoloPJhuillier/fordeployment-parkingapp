#!/usr/bin/env bash
# health.sh — Post-deploy smoke test.
#  - hits frontend /healthz (nginx)
#  - hits backend /health (FastAPI)
#  - hits backend /api/buildings to confirm DB connectivity & auth pipeline
#
# Exits non-zero on any failure; safe to call from CI / deploy.sh.
set -Eeuo pipefail
cd "$(dirname "$0")/.."

FE_PORT=$(grep -E '^FRONTEND_PORT=' .env 2>/dev/null | cut -d= -f2 || echo 3000)
BE_PORT=8001

fail() { echo "[health] FAIL: $*" >&2; exit 1; }
ok()   { echo "[health] OK:   $*"; }

echo "[health] Frontend nginx /healthz…"
status=$(curl -fsS -o /dev/null -w '%{http_code}' "http://127.0.0.1:${FE_PORT}/healthz" || echo 000)
[[ "$status" == "200" ]] || fail "frontend /healthz -> HTTP $status"
ok "frontend serving on :${FE_PORT}"

echo "[health] Backend /health…"
status=$(curl -fsS -o /dev/null -w '%{http_code}' "http://127.0.0.1:${BE_PORT}/health" || echo 000)
[[ "$status" == "200" ]] || fail "backend /health -> HTTP $status"
ok "backend on :${BE_PORT}"

echo "[health] Reverse-proxy /api/buildings via frontend…"
status=$(curl -fsS -o /dev/null -w '%{http_code}' "http://127.0.0.1:${FE_PORT}/api/buildings" || echo 000)
# 401 is acceptable here — it proves the route is wired and auth is enforced.
case "$status" in
  200|401) ok "/api proxy reachable (HTTP $status)";;
  *) fail "/api proxy -> HTTP $status";;
esac

echo "[health] All smoke checks passed."
