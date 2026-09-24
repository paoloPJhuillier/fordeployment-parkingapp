# Docker Deployment Guide — Cebuana Lhuillier Parking Reservation

> **Scope.** This guide walks through deploying the full stack (FastAPI backend + React frontend + database) using Docker Compose. It covers three configurations: **MongoDB in-container** (self-contained demo/staging), **Couchbase Capella** (cloud production), and **Couchbase Enterprise on Huawei Cloud Stack** (on-prem production).

> 🛠️ **Going to Huawei Cloud Stack?** Two flavours, depending on the target runtime:
> - **CCE (Cloud Container Engine — Kubernetes) + OBS for file storage** — the customer's production target. Use **[`ONPREM_HCS_CCE_RUNBOOK.md`](./ONPREM_HCS_CCE_RUNBOOK.md)** with the manifests under `deploy/k8s/`.
> - **Single VM with Docker Compose + local volume** — used for small/staging installs. Use **[`ONPREM_HCS_RUNBOOK.md`](./ONPREM_HCS_RUNBOOK.md)**.
>
> The sections in this file are the general background; the two runbooks above are what your Ops team actually executes.

---

## 1. Is it ready for Dockerized deployment?

**Short answer:** Yes, with the files provided in this repo. The app was built to be 12-factor-friendly, and the remaining tightenings have been applied.

| Area | Status | Notes |
|------|--------|-------|
| Stateless backend | ✅ Ready | No in-process state beyond the upload volume. |
| Env-driven config | ✅ Ready | All URLs, secrets, ports, DB choice via env vars. |
| Health check endpoint | ✅ Ready | `GET /health` returns `{ "status": "healthy" }`. |
| DB abstraction | ✅ Ready | `DB_TYPE` toggles MongoDB ↔ Couchbase at boot. |
| Upload persistence | ✅ Ready | `UPLOAD_DIR` env var points at a mounted volume. |
| HTTPS / Secure cookies | ⚠️ Configurable | `COOKIE_SECURE=true` in prod (behind TLS), `false` for local plain-http testing. |
| Frontend production build | ✅ Ready | `yarn build` via craco; served by nginx in the frontend container. |
| Same-origin API | ✅ Ready | nginx in the frontend container reverse-proxies `/api/*` to the backend — no CORS drama. |
| Frontend env baking | ⚠️ CRA limitation | `REACT_APP_BACKEND_URL` is baked into the JS bundle at build time. The same-origin proxy approach sidesteps this. |
| TLS termination | ⚠️ Two options | (a) terminate at a corporate LB / Caddy / Traefik in front of Compose, OR (b) terminate at the frontend container — see the HCS runbook for the second pattern (`nginx.onprem.conf`). |
| Secrets management | ⚠️ Manual | Put real secrets in `.env` (never commit); for production, prefer Docker Secrets, AWS SSM, or Vault. |
| Egress IP allowlisting for Capella | ⚠️ External | Your prod host's egress IP must be in Capella's Allowed IPs list. |

---

## 2. What's in the box

```
/app
├── backend/
│   ├── Dockerfile              # python:3.11-slim + uvicorn
│   └── .dockerignore
├── frontend/
│   ├── Dockerfile              # multi-stage: node:20 build -> nginx:1.27 runtime
│   ├── nginx.conf              # SPA + /api reverse proxy
│   └── .dockerignore
├── docker-compose.yml          # backend + frontend + optional mongo
└── .env.example                # copy to .env and fill in secrets
```

---

## 3. Deployment scenarios

### Scenario A — Self-contained stack on one host (MongoDB)

Use this for staging, internal demos, or on-prem deployments where you want zero external dependencies.

```bash
cd /app
cp .env.example .env

# EDIT .env — at minimum:
#   JWT_SECRET=<openssl rand -hex 64>
#   DB_TYPE=mongodb
#   COOKIE_SECURE=false        # if behind plain http (dev/demo only)
#   COOKIE_SECURE=true         # if behind TLS (recommended)

docker compose up -d --build
docker compose logs -f backend
```

The stack exposes:

- Frontend (nginx + React SPA): `http://localhost:3000`
- Backend (direct, for health checks): `http://127.0.0.1:8001/health`
- MongoDB (container-internal only)

The default admin account `admin.test@cebuana.com / Test123!` is seeded on first boot if no admin exists.

### Scenario B — Production against Couchbase Capella

Use this when your dataset lives in Capella (or an on-prem Couchbase Enterprise cluster). The Mongo container is skipped.

```bash
cp .env.example .env

# EDIT .env:
#   DB_TYPE=couchbase
#   COUCHBASE_CONNECTION_STRING=couchbases://<cluster>.cloud.couchbase.com
#   COUCHBASE_BUCKET=<your_bucket>
#   COUCHBASE_USERNAME=<db_user>
#   COUCHBASE_PASSWORD=<db_password>
#   JWT_SECRET=<openssl rand -hex 64>
#   COOKIE_SECURE=true         # must be true behind TLS

# Start only backend+frontend (Mongo is disabled via profile):
docker compose --profile couchbase up -d --build
```

**Before first start**, ensure the Capella cluster has:

1. **Allowed IPs** includes the host's public egress IP (`curl https://ifconfig.me`).
2. **Scopes + collections** provisioned. Run this once from a developer machine that can reach Capella:

   ```bash
   cd /app/backend
   pip install -r requirements.txt
   pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
   python scripts/provision_couchbase_collections.py
   ```

   Or do it from inside the backend container:

   ```bash
   docker compose exec backend python scripts/provision_couchbase_collections.py
   ```

3. **Existing Mongo data** migrated into Capella (if applicable):

   ```bash
   # From a machine that can reach BOTH Mongo and Capella:
   cd /app/backend
   python scripts/migrate_mongo_to_couchbase.py --wipe
   ```

   Or from inside the running backend container:

   ```bash
   docker compose exec backend python scripts/migrate_mongo_to_couchbase.py --wipe
   ```

   The admin UI also exposes a one-click **"Sync now: Mongo → Couchbase"** button on the Dashboard's Database Health card — handy during cutover.


### Scenario C — Huawei Cloud Stack on-prem (Couchbase Enterprise)

This is the **production deployment pattern** for the Cebuana on-prem environment. Highlights:

- Images live in the customer's HCS Docker registry; no internet-pull at deploy time.
- Backend talks to a **self-hosted Couchbase Enterprise** cluster over TLS, validating the cluster's private-CA cert.
- Frontend container **terminates HTTPS itself** — no separate Caddy / Traefik, certs are mounted from the host.
- A `preflight_onprem.sh` validator catches the common slip-ups (missing files, mismatched cert/key, unreachable cluster, port conflicts) before the stack ever starts.

Quick map of the moving parts (full procedure in **[`ONPREM_HCS_RUNBOOK.md`](./ONPREM_HCS_RUNBOOK.md)**):

```text
On the build host (once per release):
  ./scripts/build_and_push_images.sh
    └─ builds parking-backend + parking-frontend
       and pushes to <HCS_REGISTRY>/<NAMESPACE>/...:<TAG>

On the on-prem host (under /opt/parking):
  .env                              # populate from .env.onprem.example
  docker-compose.onprem.yml         # pulls from HCS registry (no local build)
  frontend/nginx.onprem.conf        # TLS-terminating nginx config
  tls/{fullchain.pem,privkey.pem}   # public-facing TLS material
  tls/cb-ca.pem                     # Couchbase Enterprise root cert
  deploy/                           # preflight, health, logs, backup, cleanup

  ./deploy/preflight_onprem.sh      # 8 sanity checks; exits non-zero on any failure
  make onprem-up                    # = compose up -d  +  health smoke
```

Updates are tag-bumps in `.env` followed by `make onprem-update`. Rollback = same flow with the previous tag. Bring-down without data loss is `make onprem-down`. The Couchbase cluster is unaffected by any of these — it lives outside the compose stack.

---
---

## 4. TLS / HTTPS

The Compose stack intentionally stops at plain-http on port 3000. For production, terminate TLS in front of it. Three common recipes:

### 4.1 Caddy (simplest, auto-HTTPS)

```Caddyfile
parking.example.com {
    reverse_proxy frontend:80
}
```

Add Caddy as a service to `docker-compose.yml` or run it separately and put Compose services on a shared Docker network.

### 4.2 Traefik (label-driven)

Add labels to the `frontend` service:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.parking.rule=Host(`parking.example.com`)"
  - "traefik.http.routers.parking.entrypoints=websecure"
  - "traefik.http.routers.parking.tls.certresolver=letsencrypt"
  - "traefik.http.services.parking.loadbalancer.server.port=80"
```

### 4.3 Cloud load balancers

On AWS / GCP / Azure, put the Compose stack behind an ALB / GLB and let the LB handle TLS. Make sure the LB passes `X-Forwarded-Proto: https` — the backend is started with `--proxy-headers --forwarded-allow-ips='*'` so it will honor it.

---

## 5. Secrets management

For anything beyond a demo, don't put real secrets in `.env` on disk.

- **Docker Swarm** — use `docker secret create` and reference via `secrets:` in the service definition.
- **Kubernetes** — use a `Secret` object and mount as env vars or files.
- **AWS ECS** — pull from **AWS Secrets Manager** or **SSM Parameter Store** via task definition `secrets`.
- **HashiCorp Vault** — sidecar injects secrets at runtime.

At minimum, rotate `JWT_SECRET` per-environment and never share it across prod/staging.

---

## 6. Persistent state

Two Docker volumes are used:

| Volume | Purpose | Contents |
|--------|---------|----------|
| `mongo_data` | MongoDB WiredTiger storage | Only when `DB_TYPE=mongodb` |
| `parking_uploads` | Floor-layout images uploaded by admins | Always |

Back them up with your usual Docker volume backup strategy (e.g., `docker run --rm -v parking_uploads:/data -v $PWD:/backup alpine tar czf /backup/uploads.tgz -C /data .`).

In Couchbase mode you only need to back up `parking_uploads` — the database is managed by Capella.

---

## 7. Operations cheat sheet

```bash
# Tail backend logs
docker compose logs -f backend

# Execute a one-off command
docker compose exec backend bash

# Run a regression pytest from the container
docker compose exec backend pytest -q

# Flip to Couchbase without rebuilding
echo "DB_TYPE=couchbase" >> .env
docker compose up -d --no-deps --force-recreate backend

# Rebuild just the frontend (e.g., after a UI change)
docker compose up -d --no-deps --build frontend

# Roll back to the previous image
docker compose up -d --no-deps backend --image parking-backend:<prev-tag>

# Verify which DB is active (admin JWT required)
curl -H "Authorization: Bearer $TOKEN" http://localhost:3000/api/system/db-info
```

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `401` on login with correct password | `COOKIE_SECURE=true` but browser is on plain http | Set `COOKIE_SECURE=false` for dev, or front with TLS for prod |
| Backend keeps restarting, logs show `ConnectError` to Capella | Host's egress IP not allowlisted in Capella | Add `curl https://ifconfig.me` output to Capella → Settings → Allowed IPs |
| `CollectionAlreadyExistsException` during provisioning | Harmless; re-running is idempotent | Ignore |
| Frontend calls hit `/api/...` with 502 from nginx | Backend container is down or not healthy yet | `docker compose logs backend`; wait for `Application startup complete.` |
| Slow startup on Couchbase (first boot) | GSI indexes being created in parallel (~10–30 s one-time) | Normal on fresh bucket; subsequent starts are instant |
| Uploaded images disappear after redeploy | Forgot to mount the `parking_uploads` volume | Don't remove the named volume when redeploying |

---

## 9. Minimum production checklist

Before flipping DNS:

- [ ] `.env` has a strong, unique `JWT_SECRET`
- [ ] `COOKIE_SECURE=true` and TLS is terminated in front of the stack
- [ ] Capella `Allowed IPs` includes the host's egress IP (if `DB_TYPE=couchbase`)
- [ ] `parking_uploads` volume is backed up nightly
- [ ] A default admin password was changed from the seeded `Test123!`
- [ ] Log shipping configured (`docker compose logs -f` → your log store)
- [ ] Uptime monitoring pings `GET /health` and `GET /healthz` (frontend)
- [ ] `docker compose exec backend pytest` passes against the production image


---

## 10. One-command operations (deploy/, Makefile)

A set of vetted shell scripts under `./deploy/` (and matching `make` targets at the repo root) wrap every routine ops action. Every script is idempotent, exits non-zero on failure, and reads `.env` so a single source of truth drives both Compose and the helpers.

| Action                               | Script                              | Make target                |
|--------------------------------------|-------------------------------------|----------------------------|
| First deploy (default / Mongo)       | `./deploy/deploy.sh`                | `make deploy`              |
| First deploy (Couchbase Capella)     | `./deploy/deploy.sh couchbase`      | `make deploy-couchbase`    |
| Forced no-cache rebuild              | `FORCE_REBUILD=1 ./deploy/deploy.sh`| `make rebuild`             |
| Rolling update (rebuild + recreate)  | `./deploy/update.sh [couchbase]`    | `make update[-couchbase]`  |
| Stop containers (data preserved)     | `./deploy/teardown.sh`              | `make teardown`            |
| Stop **and** delete data volumes     | `./deploy/teardown.sh --purge`      | `make purge`               |
| Snapshot Mongo + uploads to `./backups/` | `./deploy/backup.sh`            | `make backup`              |
| Restore from a snapshot folder       | `./deploy/restore.sh ./backups/<ts>`| `make restore SRC=...`     |
| Tail logs (one or all services)      | `./deploy/logs.sh [backend\|frontend\|mongo]` | `make logs[-...]`|
| Post-deploy smoke test               | `./deploy/health.sh`                | `make health`              |
| Backend / frontend container shell   | —                                   | `make shell-backend`, `make shell-frontend` |

`deploy.sh` runs pre-flight checks before anything starts:

1. **Docker present** — fails fast if `docker` or `docker compose` is missing.
2. **`.env` present** — copies `.env.example` if missing and bails out so the operator can fill in secrets.
3. **`JWT_SECRET` not the placeholder** — refuses to deploy with the throw-away dev value.
4. **Couchbase profile** — refuses to deploy if any `COUCHBASE_*` var is empty.
5. **Healthy wait loop** — polls `docker compose ps` for up to 120 s and surfaces unhealthy services.
6. **Smoke test** — calls `health.sh` (frontend `/healthz`, backend `/health`, reverse-proxied `/api/buildings`) before declaring success.

### First-admin override

Production deployments should never ship with the dev seed credentials. Set:

```dotenv
FIRST_ADMIN_EMAIL=ops@your-org.com
FIRST_ADMIN_PASSWORD=<32+ char random>
FIRST_ADMIN_COMPANY=Your Org
```

If these are blank, the backend logs a `WARNING: Seeding admin with DEV defaults …` line at startup so it can never go unnoticed. The seed only runs once — when no admin row exists — so rotating these env vars later does **not** clobber an existing admin.

### Backup format

`./deploy/backup.sh` writes to `./backups/<UTC-ISO-timestamp>/` containing:

- `mongo-<DB_NAME>.archive` — `mongodump --archive` stream (skipped on Couchbase profile; use Capella's built-in backups instead).
- `uploads.tar.gz` — the contents of the `parking_uploads` named volume.

Restore is symmetric: `./deploy/restore.sh ./backups/<ts>` will `mongorestore --drop` (overwriting the current DB) **only after** typing `RESTORE` at the confirmation prompt.

### CI/CD integration

`health.sh` exits non-zero on any failure, so wire it as the final post-deploy step in your pipeline:

```yaml
- name: Smoke test
  run: ./deploy/health.sh
```

### Hardened production checklist (updated)

- [ ] `.env` has a strong, unique `JWT_SECRET` (`openssl rand -hex 64`)
- [ ] `FIRST_ADMIN_EMAIL` + `FIRST_ADMIN_PASSWORD` set to a customer-owned credential (not the dev defaults)
- [ ] `COOKIE_SECURE=true` and TLS terminated upstream (Caddy / Traefik / ALB)
- [ ] Capella `Allowed IPs` includes the deploy host's egress IP (Couchbase profile only)
- [ ] `./deploy/backup.sh` scheduled via cron (e.g. nightly: `0 2 * * * cd /opt/parking && ./deploy/backup.sh`)
- [ ] Backups offsited (S3 / GCS / Azure Blob) — the `./backups/` folder is otherwise just a local copy
- [ ] Uptime monitor pings both `/healthz` (frontend) and `/health` (backend) every minute
- [ ] Log shipping in place (`docker compose logs -f` piped to Loki / CloudWatch / Stackdriver)
- [ ] Tested `./deploy/restore.sh` end-to-end on a staging environment before the first prod incident

---

## 11. Couchbase Enterprise (self-hosted) deployment

> 🛠️ **For HCS specifically, use [`ONPREM_HCS_RUNBOOK.md`](./ONPREM_HCS_RUNBOOK.md) — it's the complete bring-up procedure including registry, TLS termination, and preflight. The section below is the general background that applies to *any* on-prem Couchbase Enterprise target.**

The `couchbase` profile works equally well against **Capella** (managed cloud) and **Couchbase Enterprise** (self-hosted, on-prem or your own VPC). The connection string + auth are identical; only TLS trust and timeout tuning differ.

### What changes vs Capella

| Concern | Capella (default) | Enterprise (self-hosted) |
|---|---|---|
| Connection scheme | `couchbases://...` (TLS mandatory) | `couchbases://...` (recommended) or `couchbase://...` for non-TLS LAN |
| Trust chain | Public CA — SDK trusts out of the box | Usually private CA → must mount the CA cert |
| Network latency | Cloud / WAN | LAN |
| `wan_development` SDK profile | Applied (longer timeouts) | Skipped (LAN doesn't need it) |
| IP allowlisting | Required (Capella console) | N/A (network is yours) |
| Backups | Capella native | `cbbackupmgr` or your own snapshot strategy |

### Environment configuration

Add to your `.env`:

```dotenv
DB_TYPE=couchbase

# Common to both Capella and Enterprise:
COUCHBASE_CONNECTION_STRING=couchbases://cb.your-internal-domain.local
COUCHBASE_BUCKET=db_parking
COUCHBASE_USERNAME=parking_app
COUCHBASE_PASSWORD=...

# --- Enterprise-specific tuning ---
# Tells the adapter NOT to apply the WAN profile.
COUCHBASE_DEPLOYMENT=enterprise

# CA cert for the Enterprise cluster — mount the host file and tell the
# SDK where it lives inside the container. The compose.yml already binds
# the host path you set here to /etc/ssl/cb-ca.pem (read-only).
COUCHBASE_TRUST_STORE_HOST_PATH=/opt/parking/cb-ca.pem
COUCHBASE_TRUST_STORE_PATH=/etc/ssl/cb-ca.pem
```

Then deploy normally:

```bash
make deploy-couchbase
```

### Common Enterprise scenarios

**a) Standard TLS with private CA (recommended)**

Export the CA cert from your Couchbase cluster (Cluster ▸ Security ▸ Root Certificate ▸ Download), copy it to the deploy host as `/opt/parking/cb-ca.pem`, then set the two `TRUST_STORE` vars above. The SDK validates the full chain just like Capella.

**b) Plain `couchbase://` on a trusted LAN**

If your network is fully isolated (VPC, on-prem datacentre) and you've decided not to terminate TLS at the cluster, set:

```dotenv
COUCHBASE_CONNECTION_STRING=couchbase://cb.your-internal-domain.local
# COUCHBASE_TRUST_STORE_PATH not needed
```

The connection is plaintext, so this should only be used inside a private network you control end to end.

**c) Mutual-TLS (rare)**

If your cluster requires client cert auth in addition to user/password:

```dotenv
COUCHBASE_CERT_PATH=/etc/ssl/parking-app-client.pem
```

(You'll need to add another bind mount in `docker-compose.yml` for the client cert.)

**d) Self-signed cert without proper CA file (DEV ONLY)**

```dotenv
COUCHBASE_TLS_VERIFY=none
```

Disables certificate validation entirely. The backend logs this as a security regression at startup. **Never use in production** — a man-in-the-middle could pose as your cluster.

### Code-level changes required: none

`backend/database/couchbase_db.py` and `backend/database/__init__.py` already accept the optional `deployment`, `trust_store_path`, `cert_path`, and `tls_verify` parameters. Nothing else in the codebase (routes, services, scripts) cares whether the cluster is Capella or Enterprise — the adapter abstracts it cleanly. The `provision_couchbase_collections.py` and `migrate_mongo_to_couchbase.py` scripts work against either deployment with the same env file.

### Operational notes

- **Bucket and collections**: `provision_couchbase_collections.py` creates 18 collections under the `_default` scope. Run it once per fresh Enterprise cluster: `docker compose exec backend python -m scripts.provision_couchbase_collections`.
- **Migration from Mongo**: `docker compose exec backend python -m scripts.migrate_mongo_to_couchbase` works regardless of Capella/Enterprise — it talks to whatever `DB_TYPE=couchbase` resolves to.
- **Backups**: Capella's automated backups don't apply on Enterprise. Use `cbbackupmgr` from a node in the cluster, or wrap it in a scheduled sidecar container. Update `./deploy/backup.sh` if you want that integrated alongside the existing Mongo path.


---

## 12. Database cleanup & maintenance

The app already self-cleans during normal operation — three background loops in `backend/services/background.py` run continuously:

| Loop | Cadence | Action |
|---|---|---|
| `auto_mark_no_shows` | 5 min | Past pending reservations → `no_show`; auto-release the slot after the building's `no_show_release_minutes` window |
| `check_waitlist_expiry` | 1 min | "Notified" waitlist entries past their window → `expired`; promote next person |
| `auto_release_slots` | 1 min | After `release_time` each day, flip non-available slots back to `available` if no active reservation |

For **operator-driven** cleanup, the `db_cleanup` tool routes through the abstraction layer so it works identically against MongoDB (dev) and Couchbase (prod):

```bash
make cleanup-routine    # safe: same actions as the 3 loops, idempotent
make cleanup-test       # prompts; removes test_*/Test fixtures
make reset-data         # prompts; wipe DATA tables, re-seed admin (schema kept)
make reset-all          # prompts; wipe EVERYTHING, re-seed admin
```

Or directly:

```bash
docker compose exec backend python -m scripts.db_cleanup routine
docker compose exec backend python -m scripts.db_cleanup purge-test-data --yes
docker compose exec backend python -m scripts.db_cleanup reset-data --yes
docker compose exec backend python -m scripts.db_cleanup reset-all --yes
```

### Subcommand semantics

**`routine`** — idempotent maintenance, runs the same logic as the background loops in one shot. Safe to schedule via cron from outside the container as a "watchdog" in case the in-process loops ever stall.

**`purge-test-data`** — surgical removal. Targets:
- Users whose email matches `test` (case-insensitive) **and is not an admin**
- Users whose email starts with `ratelimit_reg_` or `overlap.test.`
- Buildings whose name starts with `Test ` (and all descendants — floors, slots, configs, reservations, waitlist, vehicles, event_blocks, notifications)

Useful before a customer demo or to clean fixtures left behind by automated tests on staging.

**`reset-data`** — drops every row from data tables (reservations, waitlist, vehicles, slot_registrations, ai_insights, sessions, notifications, event_blocks, **users**), re-seeds the admin from `FIRST_ADMIN_*` env vars. Buildings, floors, slots, configs survive — i.e. operational schema is preserved. Useful for staging refreshes when you want to keep the configured buildings.

**`reset-all`** — drops everything (data + buildings + floors + slots + configs + templates + site_content + migrations) and re-seeds the admin. Use only when you want a totally blank cluster and intend to re-import via `migrate_mongo_to_couchbase.py` or fresh setup.

### Couchbase note (collection-level truncate)

`reset-data` and `reset-all` issue per-document deletes through the abstraction's `delete_many({})`. For a Couchbase cluster with very large collections (millions of docs), this can be slow because it walks the bucket. A faster alternative is to drop and recreate the collection via N1QL, which we deliberately avoid in `db_cleanup` because dropping a collection also tears down all GSI indexes. If you need a fast, full wipe, instead:

```bash
# 1. Drop and recreate the bucket from the Capella console (or cbadm cli for Enterprise)
# 2. Re-provision the 18 collections + indexes
docker compose exec backend python -m scripts.provision_couchbase_collections
# 3. Re-seed admin
docker compose exec backend python -m scripts.db_cleanup reset-data --yes
```

### Production cleanup pattern (recommended cron)

```cron
# /etc/cron.d/parking-cleanup
*/15 * * * * root cd /opt/parking && ./deploy/cleanup.sh routine >> /var/log/parking-cleanup.log 2>&1
0 3   * * * root cd /opt/parking && ./deploy/backup.sh    >> /var/log/parking-backup.log 2>&1
```

`routine` is idempotent and cheap (a few queries against indexed fields), so running it every 15 min as a belt-and-suspenders to the in-process loops is harmless.

-seed admin
docker compose exec backend python -m scripts.db_cleanup reset-data --yes
```

### Production cleanup pattern (recommended cron)

```cron
# /etc/cron.d/parking-cleanup
*/15 * * * * root cd /opt/parking && ./deploy/cleanup.sh routine >> /var/log/parking-cleanup.log 2>&1
0 3   * * * root cd /opt/parking && ./deploy/backup.sh    >> /var/log/parking-backup.log 2>&1
```

`routine` is idempotent and cheap (a few queries against indexed fields), so running it every 15 min as a belt-and-suspenders to the in-process loops is harmless.

