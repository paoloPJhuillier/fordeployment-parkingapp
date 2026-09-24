#!/usr/bin/env bash
# backup.sh — Snapshot MongoDB + uploads volume to ./backups/<timestamp>/
#
# Skip Mongo step automatically if running on couchbase profile (DB_TYPE=couchbase
# in .env). For Couchbase Capella, use Capella's built-in backup tooling instead.
set -Eeuo pipefail
cd "$(dirname "$0")/.."

stamp=$(date -u +%Y%m%dT%H%M%SZ)
out="./backups/${stamp}"
mkdir -p "$out"

DB_TYPE=$(grep -E '^DB_TYPE=' .env 2>/dev/null | cut -d= -f2 || echo "couchbase")
DB_NAME=$(grep -E '^DB_NAME=' .env 2>/dev/null | cut -d= -f2 || echo "parking")

if [[ "$DB_TYPE" == "mongodb" ]]; then
  echo "[backup] Dumping MongoDB database '$DB_NAME'…"
  docker compose exec -T mongo \
    mongodump --archive --quiet --db "$DB_NAME" \
    > "${out}/mongo-${DB_NAME}.archive"
  echo "[backup]   -> ${out}/mongo-${DB_NAME}.archive  ($(du -h "${out}/mongo-${DB_NAME}.archive" | cut -f1))"
else
  echo "[backup] DB_TYPE=$DB_TYPE — skipping mongodump."
  echo "[backup]   For Capella: use the cluster's Backup tab (automated by default)."
  echo "[backup]   For Enterprise: run cbbackupmgr from a cluster node, or schedule"
  echo "[backup]   a sidecar container that calls cbbackupmgr against the cluster."
fi

echo "[backup] Tarballing parking_uploads volume…"
docker run --rm \
  -v parking-app_parking_uploads:/data:ro \
  -v "$(pwd)/${out}":/backup \
  alpine:3 \
  tar czf /backup/uploads.tar.gz -C /data .
echo "[backup]   -> ${out}/uploads.tar.gz  ($(du -h "${out}/uploads.tar.gz" | cut -f1))"

echo "[backup] Backup written to ${out}/"
echo "[backup] Restore with:  ./deploy/restore.sh ${out}"
