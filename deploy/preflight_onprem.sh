#!/usr/bin/env bash
# preflight_onprem.sh — sanity-check the on-prem host BEFORE deployment.
#
# Run this on the on-prem host with the populated .env in place. It catches
# the 95% of preventable install failures: missing files, port conflicts,
# unreachable Couchbase cluster, malformed TLS material.
#
# Usage:  ./deploy/preflight_onprem.sh
set -Eeuo pipefail
cd "$(dirname "$0")/.."

PASS=0; FAIL=0
ok()   { echo "  [ok]   $*"; PASS=$((PASS+1)); }
warn() { echo "  [warn] $*"; }
fail() { echo "  [FAIL] $*" >&2; FAIL=$((FAIL+1)); }

section() { echo; echo "== $* =="; }

# ---------- 1. .env present and parseable ----------------------------------
section "Configuration"
if [[ ! -f .env ]]; then
  fail ".env missing — copy .env.onprem.example to .env and fill in values"
  exit 1
fi
ok ".env present"

# Source it (allow comments and blank lines)
set -a; . ./.env; set +a

REQUIRED=(
  IMAGE_REGISTRY IMAGE_NAMESPACE IMAGE_TAG
  TLS_FULLCHAIN_HOST_PATH TLS_PRIVKEY_HOST_PATH
  COUCHBASE_CONNECTION_STRING COUCHBASE_BUCKET COUCHBASE_USERNAME COUCHBASE_PASSWORD
  COUCHBASE_TRUST_STORE_HOST_PATH
  JWT_SECRET FIRST_ADMIN_EMAIL FIRST_ADMIN_PASSWORD
)
for v in "${REQUIRED[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    fail "$v is empty in .env"
  else
    ok "$v set"
  fi
done

# Reject placeholders
[[ "${JWT_SECRET:-}" == "changeme"* ]] && fail "JWT_SECRET is still a placeholder — generate with: openssl rand -hex 64"
[[ "${FIRST_ADMIN_PASSWORD:-}" == "Test123!" ]] && warn "FIRST_ADMIN_PASSWORD = Test123! (dev default). Override for production."

# ---------- 2. Docker available --------------------------------------------
section "Docker engine"
if ! command -v docker >/dev/null; then
  fail "docker not on PATH"
else
  ok "docker present ($(docker --version))"
fi
if ! docker compose version >/dev/null 2>&1; then
  fail "'docker compose' plugin missing (need Docker Engine 20.10+)"
else
  ok "docker compose plugin present ($(docker compose version --short))"
fi

# ---------- 3. Files referenced by .env exist ------------------------------
section "Mounted files"
for f in "$TLS_FULLCHAIN_HOST_PATH" "$TLS_PRIVKEY_HOST_PATH" "$COUCHBASE_TRUST_STORE_HOST_PATH"; do
  if [[ -r "$f" ]]; then
    ok "$f readable"
  else
    fail "$f missing or not readable by current user ($(id -un))"
  fi
done

# nginx.onprem.conf is read by compose with relative path
[[ -r ./frontend/nginx.onprem.conf ]] || fail "./frontend/nginx.onprem.conf missing — pull a fresh release tarball"

# ---------- 4. TLS sanity --------------------------------------------------
section "TLS material"
if [[ -r "$TLS_FULLCHAIN_HOST_PATH" && -r "$TLS_PRIVKEY_HOST_PATH" ]]; then
  if openssl x509 -in "$TLS_FULLCHAIN_HOST_PATH" -noout -enddate >/dev/null 2>&1; then
    end=$(openssl x509 -in "$TLS_FULLCHAIN_HOST_PATH" -noout -enddate | cut -d= -f2)
    ok "fullchain valid; expires: $end"
  else
    fail "fullchain.pem is not a valid X.509 cert"
  fi
  if openssl pkey -in "$TLS_PRIVKEY_HOST_PATH" -noout >/dev/null 2>&1; then
    ok "privkey is a valid private key"
    # Cross-check: cert pubkey == priv pubkey
    cert_pub=$(openssl x509 -in "$TLS_FULLCHAIN_HOST_PATH" -noout -pubkey 2>/dev/null | openssl md5)
    key_pub=$(openssl pkey -in "$TLS_PRIVKEY_HOST_PATH" -pubout 2>/dev/null | openssl md5)
    if [[ "$cert_pub" == "$key_pub" ]]; then
      ok "fullchain and privkey match"
    else
      fail "fullchain and privkey DO NOT match — wrong cert/key pair"
    fi
  else
    fail "privkey is not a valid private key"
  fi
fi

# ---------- 5. Couchbase reachability --------------------------------------
section "Couchbase reachability"
host=$(echo "$COUCHBASE_CONNECTION_STRING" | sed -E 's|^couchbases?://||; s|[/?,].*$||' | head -1)
if [[ -n "$host" ]]; then
  if command -v nc >/dev/null && timeout 5 nc -zv "$host" 11207 >/dev/null 2>&1; then
    ok "TLS data port 11207 reachable on $host"
  elif command -v nc >/dev/null && timeout 5 nc -zv "$host" 11210 >/dev/null 2>&1; then
    ok "non-TLS data port 11210 reachable on $host (consider switching to couchbases://)"
  else
    warn "couldn't reach $host on Couchbase ports — check firewall / DNS"
  fi
fi

# ---------- 6. Host port conflicts -----------------------------------------
section "Host port availability"
for port in "${HTTP_PORT:-80}" "${HTTPS_PORT:-443}"; do
  if ss -tlnH "sport = :$port" 2>/dev/null | grep -q .; then
    fail "TCP port $port already in use on host"
  else
    ok "TCP port $port free"
  fi
done

# ---------- 7. Disk space --------------------------------------------------
section "Disk space"
free_gb=$(df -BG --output=avail / | tail -1 | tr -d 'G ')
if [[ "$free_gb" -lt 5 ]]; then
  fail "Less than 5 GB free on / — Docker layer cache will struggle"
else
  ok "${free_gb} GB free on /"
fi

# ---------- 8. Image pullability -------------------------------------------
section "Registry / image pull"
if docker pull "${IMAGE_REGISTRY}/${IMAGE_NAMESPACE}/parking-backend:${IMAGE_TAG:-latest}" >/dev/null 2>&1; then
  ok "backend image pullable from registry"
else
  warn "couldn't pull backend image — make sure 'docker login ${IMAGE_REGISTRY}' has been done by this user"
fi

# ---------- Summary --------------------------------------------------------
echo
echo "================================================================"
if [[ "$FAIL" -gt 0 ]]; then
  echo "RESULT: $FAIL check(s) FAILED, $PASS passed. Fix the FAILs before bringing the stack up."
  exit 1
else
  echo "RESULT: ALL $PASS checks passed. You're cleared for: docker compose -f docker-compose.onprem.yml --env-file .env up -d"
fi
