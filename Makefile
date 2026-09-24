# Convenience wrapper around ./deploy/*.sh
# Usage:  make deploy | make logs | make backup | ...

.PHONY: help deploy deploy-dev update update-dev teardown purge \
	backup restore logs logs-backend logs-frontend logs-mongo health \
	shell-backend shell-frontend rebuild \
	cleanup-routine cleanup-test reset-data reset-all \
	build-images push-images save-images preflight-onprem \
	onprem-up onprem-down onprem-update

help:
	@echo "Parking App — deployment targets"
	@echo "  make deploy             Build + start (Couchbase production default)"
	@echo "  make deploy-dev         Build + start with bundled MongoDB (dev only)"
	@echo "  make update             Rebuild and rolling-restart (Couchbase)"
	@echo "  make update-dev         Same, dev-mongo profile"
	@echo "  make rebuild            FORCE_REBUILD=1 (no-cache) deploy"
	@echo "  make teardown           Stop containers, KEEP data volumes"
	@echo "  make purge              Stop AND delete data volumes (irreversible)"
	@echo "  make backup             Snapshot DB + uploads to ./backups/"
	@echo "  make restore SRC=path   Restore from ./backups/<timestamp>"
	@echo "  make health             Post-deploy smoke test"
	@echo "  make cleanup-routine    Run safe maintenance (no-show flip, etc.)"
	@echo "  make cleanup-test       Remove obvious test fixtures"
	@echo "  make reset-data         DESTRUCTIVE: wipe data, keep schema"
	@echo "  make reset-all          DESTRUCTIVE: wipe everything"
	@echo "  make logs               Tail all logs"
	@echo "  make logs-backend       Tail backend only"
	@echo "  make logs-frontend      Tail frontend only"
	@echo "  make logs-mongo         Tail mongo (dev-mongo profile only)"
	@echo "  make shell-backend      Open a shell in the backend container"
	@echo "  make shell-frontend     Open a shell in the frontend container"
	@echo ""
	@echo "  --- On-prem (Huawei Cloud Stack) ---"
	@echo "  make build-images       Build + push parking-backend & frontend to HCS registry"
	@echo "  make save-images        Same as build-images, but also writes tar.gz bundles"
	@echo "  make preflight-onprem   Validate the on-prem host before bringing the stack up"
	@echo "  make onprem-up          docker compose -f docker-compose.onprem.yml up -d + health"
	@echo "  make onprem-down        Stop on-prem stack (data preserved)"
	@echo "  make onprem-update      Pull new image tag from registry, rolling-restart"

deploy:
	./deploy/deploy.sh

deploy-dev:
	./deploy/deploy.sh dev-mongo

rebuild:
	FORCE_REBUILD=1 ./deploy/deploy.sh

update:
	./deploy/update.sh

update-dev:
	./deploy/update.sh dev-mongo

teardown:
	./deploy/teardown.sh

purge:
	./deploy/teardown.sh --purge

backup:
	./deploy/backup.sh

restore:
	@test -n "$(SRC)" || (echo "Usage: make restore SRC=./backups/<timestamp>"; exit 1)
	./deploy/restore.sh $(SRC)

health:
	./deploy/health.sh

cleanup-routine:
	./deploy/cleanup.sh routine

cleanup-test:
	./deploy/cleanup.sh purge-test-data

reset-data:
	./deploy/cleanup.sh reset-data

reset-all:
	./deploy/cleanup.sh reset-all

logs:
	./deploy/logs.sh

logs-backend:
	./deploy/logs.sh backend

logs-frontend:
	./deploy/logs.sh frontend

logs-mongo:
	./deploy/logs.sh mongo

shell-backend:
	docker compose exec backend sh

shell-frontend:
	docker compose exec frontend sh

# --- On-prem (Huawei Cloud Stack) ------------------------------------------
build-images:
	./scripts/build_and_push_images.sh

push-images: build-images

save-images:
	./scripts/build_and_push_images.sh --save

preflight-onprem:
	./deploy/preflight_onprem.sh

onprem-up:
	docker compose -f docker-compose.onprem.yml --env-file .env up -d
	./deploy/health.sh

onprem-down:
	docker compose -f docker-compose.onprem.yml --env-file .env down

onprem-update:
	docker compose -f docker-compose.onprem.yml --env-file .env pull
	docker compose -f docker-compose.onprem.yml --env-file .env up -d
	./deploy/health.sh

