#!/usr/bin/env bash
# teardown.sh — Stop and remove the parking app containers.
#
# Usage:
#   ./deploy/teardown.sh            # stop containers, keep volumes (data preserved)
#   ./deploy/teardown.sh --purge    # ALSO remove mongo_data + parking_uploads volumes
set -Eeuo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--purge" ]]; then
  read -rp "This DELETES the mongo_data and parking_uploads volumes. Type DELETE to confirm: " ack
  [[ "$ack" == "DELETE" ]] || { echo "Aborted."; exit 1; }
  docker compose --profile dev-mongo down -v
  echo "[teardown] Containers + volumes removed."
else
  docker compose --profile dev-mongo down
  echo "[teardown] Containers stopped. Volumes preserved."
fi
