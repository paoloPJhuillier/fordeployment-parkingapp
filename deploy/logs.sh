#!/usr/bin/env bash
# logs.sh — Tail logs for one service, or all of them.
#
# Usage:
#   ./deploy/logs.sh                    # all services
#   ./deploy/logs.sh backend
#   ./deploy/logs.sh frontend
#   ./deploy/logs.sh mongo
#   LINES=500 ./deploy/logs.sh backend  # show last 500 lines
set -Eeuo pipefail
cd "$(dirname "$0")/.."

LINES="${LINES:-200}"
svc="${1:-}"

if [[ -z "$svc" ]]; then
  docker compose logs --tail "$LINES" -f
else
  docker compose logs --tail "$LINES" -f "$svc"
fi
