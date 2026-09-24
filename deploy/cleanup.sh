#!/usr/bin/env bash
# cleanup.sh — wrapper around backend/scripts/db_cleanup.py.
#
# Usage:
#   ./deploy/cleanup.sh routine            # safe maintenance
#   ./deploy/cleanup.sh purge-test-data    # remove obvious test fixtures
#   ./deploy/cleanup.sh reset-data         # DESTRUCTIVE — wipe data, keep schema
#   ./deploy/cleanup.sh reset-all          # DESTRUCTIVE — wipe everything
#
# Routes through the running backend container so DB_TYPE / Couchbase TLS /
# trust-store config picked up automatically from .env. If no backend is
# running, the helper prints a hint and exits.
set -Eeuo pipefail
cd "$(dirname "$0")/.."

cmd="${1:-}"
case "$cmd" in
  routine|purge-test-data|reset-data|reset-all) ;;
  *)
    cat <<EOF
Usage: $0 <command>

  routine            Idempotent: no-shows, waitlist expiry, slot release
  purge-test-data    Remove fixtures (test_*@*, 'Test ' buildings)
  reset-data         DESTRUCTIVE: wipe data tables + re-seed admin
  reset-all          DESTRUCTIVE: wipe everything + re-seed admin
EOF
    exit 1
    ;;
esac

if ! docker compose ps backend --status running --quiet | grep -q .; then
  echo "ERROR: backend container is not running. Start the stack first: make deploy" >&2
  exit 1
fi

# Destructive cmds: confirm at the wrapper layer too.
case "$cmd" in
  reset-data|reset-all|purge-test-data)
    read -rp "About to run '$cmd'. Type DELETE to confirm: " ack
    [[ "$ack" == "DELETE" ]] || { echo "Aborted."; exit 1; }
    ;;
esac

echo "[cleanup] Running: $cmd"
docker compose exec -T backend python -m scripts.db_cleanup "$cmd" --yes
echo "[cleanup] Done."
