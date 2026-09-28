#!/usr/bin/env bash
# couchbase-init.sh — one-shot, idempotent Couchbase cluster provisioning.
#
# Runs inside a couchbase:community image (has couchbase-cli + curl) against
# the couchbase service. Safe to re-run: every step tolerates "already done".
#
# Env (provided by compose):
#   CB_HOST      hostname of the couchbase node (e.g. "couchbase")
#   CB_USERNAME  admin username to create / use
#   CB_PASSWORD  admin password to create / use
#   CB_BUCKET    bucket name to create
#   CB_RAM_MB    bucket + data service RAM quota (MB)
set -uo pipefail

CB_HOST="${CB_HOST:-couchbase}"
CB_RAM_MB="${CB_RAM_MB:-512}"
BASE="http://${CB_HOST}:8091"

log() { echo "[cb-init] $*"; }

# --- Wait for the REST port to answer ---------------------------------------
log "waiting for ${BASE} ..."
for i in $(seq 1 60); do
  if curl -sf "${BASE}/ui/index.html" >/dev/null 2>&1; then
    log "node is up"
    break
  fi
  sleep 3
done

# --- Initialize the cluster (no-op if already initialized) ------------------
log "initializing cluster node (data,index,query) ..."
INIT_OUT="$(couchbase-cli cluster-init \
  --cluster "${BASE}" \
  --cluster-username "${CB_USERNAME}" \
  --cluster-password "${CB_PASSWORD}" \
  --services data,index,query \
  --cluster-ramsize "${CB_RAM_MB}" \
  --cluster-index-ramsize 256 2>&1)"
if echo "${INIT_OUT}" | grep -qiE "SUCCESS|already initialized|_init is set"; then
  log "cluster initialized (or already was)"
else
  log "cluster-init output: ${INIT_OUT}"
fi

# --- Create the bucket (no-op if it already exists) -------------------------
log "creating bucket '${CB_BUCKET}' ..."
BKT_OUT="$(couchbase-cli bucket-create \
  --cluster "${BASE}" \
  --username "${CB_USERNAME}" \
  --password "${CB_PASSWORD}" \
  --bucket "${CB_BUCKET}" \
  --bucket-type couchbase \
  --bucket-ramsize "${CB_RAM_MB}" \
  --wait 2>&1)"
if echo "${BKT_OUT}" | grep -qiE "SUCCESS|already exists"; then
  log "bucket ready"
else
  log "bucket-create output: ${BKT_OUT}"
fi

# --- Wait until the query service is reachable ------------------------------
log "waiting for query service ..."
for i in $(seq 1 30); do
  if curl -sf -u "${CB_USERNAME}:${CB_PASSWORD}" \
      "http://${CB_HOST}:8093/query/service" \
      -d "statement=SELECT 1" >/dev/null 2>&1; then
    log "query service is up"
    break
  fi
  sleep 3
done

# --- Create the 18 app collections under the _default scope -----------------
# Keep this list in sync with backend/scripts/provision_couchbase_collections.py
COLLECTIONS="users sessions buildings floors parking_slots vehicles zones \
parking_configs building_policies slot_registrations reservations \
waitlist_entries event_blocks notifications site_content templates \
ai_insights migrations"

log "creating collections under \`${CB_BUCKET}\`._default ..."
for c in ${COLLECTIONS}; do
  couchbase-cli collection-manage \
    --cluster "${BASE}" \
    --username "${CB_USERNAME}" \
    --password "${CB_PASSWORD}" \
    --bucket "${CB_BUCKET}" \
    --create-collection "_default.${c}" \
    >/dev/null 2>&1 \
    && log "  + ${c}" \
    || log "  = ${c} (exists or skipped)"
done

# Give KV/query a moment to see the new collections, then build a primary
# index on each so the app's N1QL SELECTs work out of the box.
sleep 5
log "ensuring primary indexes on each collection ..."
for c in ${COLLECTIONS}; do
  curl -sf -u "${CB_USERNAME}:${CB_PASSWORD}" \
    "http://${CB_HOST}:8093/query/service" \
    --data-urlencode "statement=CREATE PRIMARY INDEX IF NOT EXISTS ON \`${CB_BUCKET}\`.\`_default\`.\`${c}\`" \
    >/dev/null 2>&1 \
    && log "  idx ${c}" \
    || log "  idx ${c} (deferred)"
done

log "provisioning complete"
