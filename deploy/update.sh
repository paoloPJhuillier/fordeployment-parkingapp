#!/usr/bin/env bash
# update.sh — Rolling update for a running stack.
#  - rebuilds images with current source
#  - recreates services one at a time so traffic stays up between containers
#  - re-runs the smoke test
#
# Usage:
#   ./deploy/update.sh            # default profile
#   ./deploy/update.sh couchbase
set -Eeuo pipefail
cd "$(dirname "$0")/.."

PROFILE="${1:-default}"

echo "[update] Pulling latest base images…"
docker compose pull --ignore-buildable || true

echo "[update] Rebuilding application images…"
if [[ "$PROFILE" == "dev-mongo" ]]; then
  DB_TYPE=mongodb docker compose --profile dev-mongo build
else
  docker compose build
fi

echo "[update] Recreating backend (graceful)…"
if [[ "$PROFILE" == "dev-mongo" ]]; then
  DB_TYPE=mongodb docker compose --profile dev-mongo up -d --no-deps backend
else
  docker compose up -d --no-deps backend
fi
sleep 4

echo "[update] Recreating frontend (zero-downtime to user from nginx side)…"
if [[ "$PROFILE" == "dev-mongo" ]]; then
  DB_TYPE=mongodb docker compose --profile dev-mongo up -d --no-deps frontend
else
  docker compose up -d --no-deps frontend
fi
sleep 4

"$(dirname "$0")/health.sh"
echo "[update] Update complete."
