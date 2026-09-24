#!/usr/bin/env bash
# restore.sh — Restore MongoDB + uploads from a ./backups/<timestamp>/ folder.
#
# Usage:
#   ./deploy/restore.sh ./backups/20260429T120000Z
set -Eeuo pipefail
cd "$(dirname "$0")/.."

src="${1:-}"
if [[ -z "$src" || ! -d "$src" ]]; then
  echo "Usage: $0 <backup-folder>" >&2
  echo "Available backups:" >&2
  ls -1d backups/* 2>/dev/null || echo "  (none)"
  exit 1
fi

DB_NAME=$(grep -E '^DB_NAME=' .env 2>/dev/null | cut -d= -f2 || echo "parking")

read -rp "This OVERWRITES current data with $src. Type RESTORE to confirm: " ack
[[ "$ack" == "RESTORE" ]] || { echo "Aborted."; exit 1; }

archive=$(ls "${src}"/mongo-*.archive 2>/dev/null | head -1 || true)
if [[ -n "$archive" ]]; then
  echo "[restore] Restoring MongoDB from $archive…"
  docker compose exec -T mongo \
    mongorestore --archive --drop --quiet \
    < "$archive"
fi

if [[ -f "${src}/uploads.tar.gz" ]]; then
  echo "[restore] Restoring uploads volume…"
  docker run --rm \
    -v parking-app_parking_uploads:/data \
    -v "$(pwd)/${src}":/backup:ro \
    alpine:3 \
    sh -c "rm -rf /data/* && tar xzf /backup/uploads.tar.gz -C /data"
fi

echo "[restore] Done. Restart backend so caches are clean: docker compose restart backend"
