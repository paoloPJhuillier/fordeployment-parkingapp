# Parking Reservation — Huawei Cloud Stack On-Prem Runbook (Single-VM / Docker Compose)

> ⚠️ **Picking the right runbook**
> - Deploying to **CCE (Cloud Container Engine — Kubernetes)** with **OBS** for file storage? Use [`ONPREM_HCS_CCE_RUNBOOK.md`](./ONPREM_HCS_CCE_RUNBOOK.md). That is the customer's production target.
> - Deploying to a **single HCS VM** with Docker + Docker Compose, files on a local volume? Stay on this document.

This is the **single document** for bringing the parking app up on a Huawei Cloud Stack (HCS) on-prem environment. It assumes:

- A Couchbase Enterprise cluster already exists inside the customer's network.
- The customer has a private Docker registry on HCS (SWR-style or generic).
- TLS will be terminated at the frontend container (we ship and they own the certs).
- Internet access is restricted — images must be uploaded to the HCS registry from a build machine, not pulled from Docker Hub at deploy time.
- No data is being migrated; the install starts fresh with a default admin.

Everything below is sequential. Don't skip steps; the preflight script catches the common slip-ups.

---

## 1. What you'll need before you start

### Hosts

| Role         | Notes                                                                    |
|--------------|--------------------------------------------------------------------------|
| Build host   | A dev machine OR a CI runner with Docker installed AND outbound internet. Used once per release to build images. |
| On-prem host | The HCS VM that will run the containers. Docker 20.10+ with the compose v2 plugin. ~5 GB free disk. |
| Couchbase    | An existing Enterprise cluster reachable from the on-prem host on TLS port 11207. |

### Files / values you'll collect

- HCS registry hostname, e.g. `registry.your-hcs.local` (and your username / password / robot token).
- The image namespace / project, e.g. `cebuana-parking`.
- A version tag, e.g. `v1.0.0`.
- TLS cert + key for the public hostname users will hit, in PEM format:
  - `fullchain.pem` — server cert + all intermediate CAs (NOT the root)
  - `privkey.pem` — matching private key, no passphrase
- The Couchbase cluster's Root Certificate (`cb-ca.pem`) — download from `Web Console → Security → Root Certificate`.
- Couchbase connection string (`couchbases://...`), bucket, app username, app password.
- Two random strings:
  - `JWT_SECRET` — generate with `openssl rand -hex 64`
  - `FIRST_ADMIN_PASSWORD` — anything strong (≥ 16 chars), customer-owned

---

## 2. On the build host: produce + push the images

### 2a. Clone the release tag

```bash
git clone <repo-url> parking-app
cd parking-app
git checkout v1.0.0           # whichever tag you're shipping
```

### 2b. Build & push (single script)

```bash
./scripts/build_and_push_images.sh
```

The script prompts for `IMAGE_REGISTRY`, `IMAGE_NAMESPACE`, `IMAGE_TAG`, then:

1. Builds `parking-backend` from `./backend/Dockerfile` (Python 3.11 slim, ~250 MB).
2. Builds `parking-frontend` from `./frontend/Dockerfile` (multi-stage Node 20 → Nginx 1.27 alpine, ~70 MB).
3. `docker login` to the HCS registry (or uses `REGISTRY_USERNAME`/`REGISTRY_PASSWORD` env vars).
4. `docker push` both images.

### 2c. Air-gapped variant

If the build host can't reach the HCS registry directly, add `--save`:

```bash
./scripts/build_and_push_images.sh --save
```

You'll get `./offline-bundle/parking-{backend,frontend}-vX.Y.Z.tar.gz` (~120 MB compressed). Transfer those to the on-prem host (or to a jump host that can push to HCS) and:

```bash
gunzip -c parking-backend-v1.0.0.tar.gz  | docker load
gunzip -c parking-frontend-v1.0.0.tar.gz | docker load
docker push registry.your-hcs.local/cebuana-parking/parking-backend:v1.0.0
docker push registry.your-hcs.local/cebuana-parking/parking-frontend:v1.0.0
```

---

## 3. On the on-prem host: prepare the filesystem

### 3a. Pull the deployment files

The on-prem host doesn't need the full source tree — it only needs:

- `docker-compose.onprem.yml`
- `frontend/nginx.onprem.conf`
- `.env` (you'll create this from the template)
- `deploy/preflight_onprem.sh`
- `deploy/health.sh`, `deploy/logs.sh`, `deploy/backup.sh` (operational scripts)

The simplest path: `tar czf onprem-bundle.tar.gz docker-compose.onprem.yml frontend/nginx.onprem.conf .env.onprem.example deploy/` on the build host and transfer the tarball.

Place everything under `/opt/parking/` on the on-prem host:

```text
/opt/parking/
├── docker-compose.onprem.yml
├── frontend/
│   └── nginx.onprem.conf
├── deploy/
│   ├── preflight_onprem.sh
│   ├── health.sh
│   ├── logs.sh
│   └── backup.sh
├── tls/
│   ├── fullchain.pem        # 600, owned by the docker daemon user or root
│   ├── privkey.pem          # 600, same
│   └── cb-ca.pem            # 644
└── .env                     # 600 — secrets live here
```

### 3b. Configure `.env`

```bash
cp .env.onprem.example .env
$EDITOR .env
```

Fill in EVERY value. The runbook companion `/app/.env.onprem.example` documents each one inline. Pay special attention to:

- `IMAGE_REGISTRY` / `IMAGE_NAMESPACE` / `IMAGE_TAG` — must match what you pushed in §2.
- `TLS_FULLCHAIN_HOST_PATH` and `TLS_PRIVKEY_HOST_PATH` — absolute paths to the PEM files in `/opt/parking/tls/`.
- `COUCHBASE_TRUST_STORE_HOST_PATH` — absolute path to `cb-ca.pem`.
- `JWT_SECRET` — `openssl rand -hex 64`. Don't commit, don't reuse across environments.
- `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` — these create the FIRST admin on first boot. After that, manage admins via the User Management UI; rotating these env vars later does NOT overwrite an existing admin.

### 3c. Run preflight

```bash
cd /opt/parking
./deploy/preflight_onprem.sh
```

The script will check:

- `.env` present and every required key has a non-empty value
- `docker` and `docker compose` are installed and versioned correctly
- Every file referenced by `.env` exists and is readable
- The TLS cert and key actually match (md5 of the public keys)
- The cert isn't expired (and prints the `enddate`)
- Host ports 80 and 443 aren't already taken
- The Couchbase cluster's TLS data port (11207) is reachable
- The HCS registry image actually pulls

If any check fails, fix it and re-run. The script is idempotent.

---

## 4. Bring the stack up

```bash
docker compose -f docker-compose.onprem.yml --env-file .env up -d
```

First startup pulls the two images (a few minutes), then:

- The backend connects to Couchbase, runs collection migrations, and seeds the FIRST admin if no admin exists. Watch logs:

  ```bash
  ./deploy/logs.sh backend
  ```

  Expect: `Default admin account created: <FIRST_ADMIN_EMAIL>` followed by the three background loops starting.

- The frontend container loads `nginx.onprem.conf`, binds 80 + 443, and serves the built React bundle.

### 4a. Smoke test

```bash
./deploy/health.sh
```

Checks the local health endpoints. Then verify externally:

```bash
curl -I https://your-public-hostname/healthz
# Expect: HTTP/2 200
curl -I https://your-public-hostname/api/buildings
# Expect: HTTP/2 401  (proves /api proxy works AND auth is enforced)
```

Open `https://your-public-hostname/login` in a browser; sign in with `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD`. You're live.

---

## 5. Day-2 operations

```bash
./deploy/logs.sh                         # tail all logs
./deploy/logs.sh backend                 # one service
./deploy/health.sh                       # smoke test (also exits non-zero on any failure)
./deploy/backup.sh                       # snapshots uploads volume; reminds about Couchbase backup tooling
```

For routine maintenance (no-show flip, waitlist expiry, slot release) you can let the in-process loops do their thing or call them directly:

```bash
docker compose -f docker-compose.onprem.yml exec backend python -m scripts.db_cleanup routine
```

A nightly cron is recommended:

```cron
*/15 * * * * root cd /opt/parking && docker compose -f docker-compose.onprem.yml exec -T backend python -m scripts.db_cleanup routine >> /var/log/parking-cleanup.log 2>&1
```

---

## 6. Updating to a new release

On the build host:

```bash
git pull && git checkout v1.1.0
IMAGE_TAG=v1.1.0 ./scripts/build_and_push_images.sh
```

On the on-prem host:

```bash
cd /opt/parking
$EDITOR .env                              # bump IMAGE_TAG=v1.1.0
docker compose -f docker-compose.onprem.yml --env-file .env pull
docker compose -f docker-compose.onprem.yml --env-file .env up -d
./deploy/health.sh
```

The two containers are recreated one at a time; data in the `parking_uploads` volume + Couchbase cluster is untouched.

---

## 7. Bringing the stack down

### 7a. Maintenance stop (data preserved)

```bash
docker compose -f docker-compose.onprem.yml --env-file .env down
```

### 7b. Full uninstall (DESTRUCTIVE — only the parking_uploads volume; Couchbase data is in your cluster, untouched)

```bash
docker compose -f docker-compose.onprem.yml --env-file .env down -v
```

To also remove the application data from Couchbase (e.g. for a clean reinstall):

```bash
docker compose -f docker-compose.onprem.yml --env-file .env up -d
docker compose -f docker-compose.onprem.yml exec backend python -m scripts.db_cleanup reset-all --yes
docker compose -f docker-compose.onprem.yml --env-file .env down -v
```

---

## 8. Rollback

If a release goes bad after `up -d`:

```bash
$EDITOR .env                              # set IMAGE_TAG back to the last known good
docker compose -f docker-compose.onprem.yml --env-file .env up -d
./deploy/health.sh
```

Because images are versioned in the registry and `.env` is the only thing that changes, rollback is the same flow as forward-update — just with an older tag. There's no schema migration that would prevent a rollback (Couchbase is schemaless and the app uses `id`-keyed UUIDs).

---

## 9. Troubleshooting cheat sheet

| Symptom                                              | First thing to check                                                |
|------------------------------------------------------|---------------------------------------------------------------------|
| Frontend container restarting                        | `./deploy/logs.sh frontend` — usually wrong cert path or expired TLS |
| Backend keeps restarting                             | `./deploy/logs.sh backend` — Couchbase auth fail or wrong CA cert    |
| `/api/...` returns 502                               | Backend isn't healthy yet — wait 30 s after `up -d`, then retry      |
| `/api/...` returns 401 unexpectedly                  | JWT_SECRET changed; users will need to re-login                       |
| First-login fails for the seeded admin               | Check backend log for "Default admin account created" — if absent the seed didn't run, usually because an admin already exists. Re-seed via `db_cleanup reset-data` |
| Couchbase "self-signed certificate"                  | `COUCHBASE_TRUST_STORE_PATH` not set or wrong file mounted; verify with `docker compose exec backend cat /etc/ssl/cb-ca.pem | head -2` |
| Browser shows nginx default page                     | `nginx.onprem.conf` not bind-mounted — re-check `volumes:` in compose |
| Browser shows cert warning                           | `fullchain.pem` is just the leaf cert — needs intermediates appended |

---

## 10. Reference: file checklist

Before running `up -d`, this checklist must be true on the on-prem host:

- [ ] `/opt/parking/.env` populated, mode 600
- [ ] `/opt/parking/docker-compose.onprem.yml`
- [ ] `/opt/parking/frontend/nginx.onprem.conf`
- [ ] `/opt/parking/tls/fullchain.pem` (cert + intermediates), mode 600
- [ ] `/opt/parking/tls/privkey.pem`, mode 600
- [ ] `/opt/parking/tls/cb-ca.pem` (Couchbase root cert), mode 644
- [ ] `/opt/parking/deploy/preflight_onprem.sh` — exited 0
- [ ] `docker login <IMAGE_REGISTRY>` succeeded as the user that owns the docker socket
- [ ] Couchbase Enterprise cluster reachable on TLS port 11207
- [ ] `JWT_SECRET` is not the placeholder
- [ ] `FIRST_ADMIN_PASSWORD` is not `Test123!`
- [ ] Host firewall allows 80, 443 from the user network

---

## 11. Horizontal scaling (multi-replica backend)

### Statelessness summary

| Component       | Stateless? | Notes |
|----------------|------------|-------|
| Frontend       | ✅ fully | Plain nginx + static React bundle. Scale to N replicas freely. |
| Backend (HTTP) | ✅ mostly | JWT auth (no server sessions); state lives in Couchbase. |
| Background loops | ❌ leader-only | `auto_mark_no_shows`, `check_waitlist_expiry`, `auto_release_slots`. With N replicas they all multi-fire. |
| Login rate limiter (slowapi) | ❌ per-replica | In-memory window. With N replicas an attacker effectively gets 5×N attempts/min. |
| Uploaded files (`/var/lib/parking/uploads`) | ❌ local | Replica B can't serve a file replica A wrote unless the volume is shared storage. |

### To scale out safely on HCS

**1. Designate one leader replica for background tasks.**

In `.env`, leave the default for the leader (`RUN_BACKGROUND_TASKS=true`) and supply override files for the other replicas:

```bash
# leader  (default .env)
RUN_BACKGROUND_TASKS=true

# extra replicas — point compose at an additional override file
echo "RUN_BACKGROUND_TASKS=false" > .env.replica
```

The leader replica handles the no-show flips, waitlist expiry, and slot release; the others serve only HTTP traffic. On startup each replica logs which mode it's in:

```
INFO Background maintenance loops started on this replica
INFO RUN_BACKGROUND_TASKS=false — skipping background loops on this replica
```

**2. Switch the uploads volume to a shared filesystem.**

The default `parking_uploads:` named volume is local to the Docker host. For horizontal scale-out, mount an NFS share (or CephFS, GlusterFS, HCS file storage) at `/var/lib/parking/uploads` on every replica. Example for compose:

```yaml
volumes:
  parking_uploads:
    driver: local
    driver_opts:
      type: nfs
      o: "addr=nfs.your-internal.corp,nfsvers=4,rw,soft"
      device: ":/exports/parking-uploads"
```

OR mount it from the host filesystem (where the host already has the NFS share mounted at `/mnt/parking-uploads`):

```yaml
backend:
  volumes:
    - /mnt/parking-uploads:/var/lib/parking/uploads
```

**3. Front the replicas with a load balancer.**

Stand up an HCS ELB / LVS / HAProxy in front of the frontend container. Round-robin works fine for HTTP traffic. **Enable sticky sessions only if** you care about login rate-limit coherence — otherwise `5/min × N` is your effective limit.

The frontend nginx already proxies `/api/*` to `backend:8001` by Docker DNS. To scale the backend behind that, change `docker-compose.onprem.yml`:

```yaml
backend:
  # ... existing config ...
  deploy:
    replicas: 3
```

then `docker compose up -d --scale backend=3`. Docker's internal DNS round-robins `backend` to all three replicas; the frontend nginx sees only one logical name.

**4. Couchbase Enterprise is your shared state — scale it independently.**

The cluster is the single source of truth. Scale the Couchbase nodes and the app replicas separately based on their respective load profiles.

### What we deliberately did NOT do

- **Distributed lock for background tasks.** A Couchbase-CAS-backed lease would let any replica become leader and survive failover automatically. It's the "right" answer for production resilience but adds ~200 lines and a failover test plan; for the customer's current load profile, RUN_BACKGROUND_TASKS=true on one replica + a healthcheck-based restart is operationally simpler.
- **Redis-backed slowapi limiter.** Possible (`storage_uri="redis://..."`), but introduces a new dependency. For the current threat model the per-replica limit is acceptable; revisit if login brute-force becomes a real concern.
- **S3-style object storage for uploads.** Cleaner than NFS but requires changes in `routes/buildings.py` and `config.py`. NFS is the lowest-friction path for HCS.

### Single-replica is fine

For most on-prem rollouts, ONE backend replica handles thousands of users without breaking a sweat (Couchbase, not Python, is the bottleneck). Don't preemptively scale; instrument first, then scale when you have a reason.

