#!/usr/bin/env bash
# build_and_push_images.sh — produce the two app images and push them to
# the customer's Huawei Cloud Stack Docker registry.
#
# Usage (interactive — recommended):
#   ./scripts/build_and_push_images.sh
#
# Usage (CI / scripted):
#   IMAGE_REGISTRY=registry.your-hcs.local \
#   IMAGE_NAMESPACE=cebuana-parking \
#   IMAGE_TAG=v1.0.0 \
#   REGISTRY_USERNAME=... REGISTRY_PASSWORD=... \
#       ./scripts/build_and_push_images.sh --no-prompt
#
# Add --save to ALSO write tarballs to ./offline-bundle/ for hosts that can't
# reach the registry from the build machine. The on-prem operator can then
# `docker load < parking-backend-vX.Y.Z.tar` and re-push from inside HCS.
set -Eeuo pipefail
cd "$(dirname "$0")/.."

# --- 1. Resolve config -----------------------------------------------------
NO_PROMPT=0
SAVE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-prompt) NO_PROMPT=1 ;;
    --save) SAVE=1 ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
  shift
done

prompt_var() {
  local var="$1" prompt="$2" default="${3:-}"
  if [[ -z "${!var:-}" ]]; then
    if [[ "$NO_PROMPT" == "1" ]]; then
      echo "ERROR: $var must be set in env when --no-prompt is given." >&2
      exit 2
    fi
    if [[ -n "$default" ]]; then
      read -rp "$prompt [$default]: " val
      val="${val:-$default}"
    else
      read -rp "$prompt: " val
    fi
    printf -v "$var" '%s' "$val"
  fi
}

prompt_var IMAGE_REGISTRY  "HCS Docker registry hostname (e.g. registry.your-hcs.local)"
prompt_var IMAGE_NAMESPACE "Image namespace / project (e.g. cebuana-parking)"
prompt_var IMAGE_TAG       "Image tag (semver recommended)" "v1.0.0"

BACKEND_IMG="${IMAGE_REGISTRY}/${IMAGE_NAMESPACE}/parking-backend:${IMAGE_TAG}"
FRONTEND_IMG="${IMAGE_REGISTRY}/${IMAGE_NAMESPACE}/parking-frontend:${IMAGE_TAG}"

echo
echo "[build] Will produce:"
echo "  $BACKEND_IMG"
echo "  $FRONTEND_IMG"
echo

# --- 2. Build --------------------------------------------------------------
echo "[build] Building backend image…"
docker build -t "$BACKEND_IMG" ./backend

echo "[build] Building frontend image…"
# Empty REACT_APP_BACKEND_URL = same-origin nginx proxy (correct for on-prem TLS frontend)
docker build \
  --build-arg REACT_APP_BACKEND_URL="" \
  -t "$FRONTEND_IMG" \
  ./frontend

# --- 3. Optional: emit offline tarballs ------------------------------------
if [[ "$SAVE" == "1" ]]; then
  mkdir -p ./offline-bundle
  echo "[build] Saving tarballs to ./offline-bundle/"
  docker save "$BACKEND_IMG"  | gzip > "./offline-bundle/parking-backend-${IMAGE_TAG}.tar.gz"
  docker save "$FRONTEND_IMG" | gzip > "./offline-bundle/parking-frontend-${IMAGE_TAG}.tar.gz"
  ls -lh ./offline-bundle/
  echo
  echo "[build] Transfer the .tar.gz files to the on-prem host (USB / SCP / object store)."
  echo "[build] Then on the on-prem host:"
  echo "  gunzip -c parking-backend-${IMAGE_TAG}.tar.gz  | docker load"
  echo "  gunzip -c parking-frontend-${IMAGE_TAG}.tar.gz | docker load"
  echo "  docker tag <loaded-image> ${BACKEND_IMG}"
  echo "  docker push ${BACKEND_IMG}"
  echo "  (repeat for frontend)"
fi

# --- 4. Push --------------------------------------------------------------
echo
echo "[push] Logging in to ${IMAGE_REGISTRY}…"
if [[ -n "${REGISTRY_USERNAME:-}" && -n "${REGISTRY_PASSWORD:-}" ]]; then
  echo "$REGISTRY_PASSWORD" | docker login "$IMAGE_REGISTRY" -u "$REGISTRY_USERNAME" --password-stdin
else
  docker login "$IMAGE_REGISTRY"
fi

echo "[push] Pushing $BACKEND_IMG"
docker push "$BACKEND_IMG"
echo "[push] Pushing $FRONTEND_IMG"
docker push "$FRONTEND_IMG"

echo
echo "[done] Images are now in the HCS registry."
echo "[done] On the on-prem host, populate .env with:"
echo "  IMAGE_REGISTRY=$IMAGE_REGISTRY"
echo "  IMAGE_NAMESPACE=$IMAGE_NAMESPACE"
echo "  IMAGE_TAG=$IMAGE_TAG"
echo "[done] Then: docker compose -f docker-compose.onprem.yml --env-file .env up -d"
