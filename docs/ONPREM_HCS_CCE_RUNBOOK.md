# Parking Reservation — Huawei Cloud Stack (CCE / Kubernetes) Runbook

This is the **single document** for bringing the parking app up on a Huawei Cloud Stack (HCS) on-prem environment using **CCE (Cloud Container Engine — managed Kubernetes)** and **OBS (Object Storage Service — S3-compatible)**.

> Looking for the older single-VM Docker Compose flow? See [`ONPREM_HCS_RUNBOOK.md`](./ONPREM_HCS_RUNBOOK.md). That path is still supported for small / non-clustered installs.

It assumes:

- A CCE cluster (Kubernetes 1.25+) is already provisioned in HCS, with `kubectl` access from your Ops workstation.
- A private SWR (Software Repository for Container) project exists in HCS, with credentials.
- An OBS bucket exists in HCS, plus AK/SK with read/write/delete on it.
- A Couchbase Enterprise cluster is reachable from inside the cluster on TLS port 11207.
- TLS termination is handled either by a cluster ingress controller OR by an external HCS ELB (both options ship in `deploy/k8s/`).
- No data is being migrated; the install starts fresh with a default admin.

---

## 1. What you'll need before you start

| Item | Notes |
|---|---|
| `kubectl` ≥ 1.25 | Configured against the CCE cluster (`kubectl get nodes` should work). |
| `kustomize` | Built into `kubectl apply -k`, no separate install needed for K8s ≥ 1.21. |
| Docker (build host) | Used once per release to build & push images. |
| HCS SWR creds | Registry hostname, project name, username/password (or robot token). |
| OBS bucket | Bucket name + endpoint (e.g. `https://obs.cn-north-4.your-hcs.local`) + AK/SK. |
| Couchbase | `couchbases://...` connection string, bucket, app username, app password, **root CA PEM**. |
| TLS cert (option A only) | `fullchain.pem` + `privkey.pem` for the public hostname users will hit. |
| Two random secrets | `JWT_SECRET = openssl rand -hex 64`, plus a strong `FIRST_ADMIN_PASSWORD`. |

---

## 2. Build & push container images

Same as the VM-based flow — the images are identical:

```bash
git clone <repo-url> parking-app
cd parking-app
git checkout v1.0.0

./scripts/build_and_push_images.sh
# prompts for IMAGE_REGISTRY / IMAGE_NAMESPACE / IMAGE_TAG
# e.g. swr.your-region.your-hcs.local / parking / v1.0.0
```

Air-gapped variant (build host can't reach SWR): pass `--save` and transfer the resulting tarballs as documented in [`ONPREM_HCS_RUNBOOK.md` §2c](./ONPREM_HCS_RUNBOOK.md).

After this step you should be able to:

```bash
docker pull swr.your-region.your-hcs.local/parking/parking-backend:v1.0.0
docker pull swr.your-region.your-hcs.local/parking/parking-frontend:v1.0.0
```

…from a node in the CCE cluster.

---

## 3. Provision the OBS bucket

The backend uses OBS for **uploaded floor-layout images only** (no other state). Anything else is in Couchbase or in-memory.

1. In the HCS console: **OBS → Buckets → Create**. Choose "Standard" storage class, "Private" ACL, region matching the cluster.
2. Note the **endpoint** (e.g. `https://obs.cn-north-4.your-hcs.local`) and the **bucket name** (e.g. `parking-uploads`).
3. Create an AK/SK pair with the OBS policy `OBSOnlyOperator` (or a custom policy granting `obs:object:GetObject`, `PutObject`, `DeleteObject`, `HeadObject` on the bucket).
4. Verify from a node:

   ```bash
   AWS_ACCESS_KEY_ID=<AK> AWS_SECRET_ACCESS_KEY=<SK> \
   aws --endpoint-url https://obs.cn-north-4.your-hcs.local \
       s3 ls s3://parking-uploads/
   ```

---

## 4. Stage the Kubernetes manifests

On your Ops workstation:

```bash
cd parking-app/deploy/k8s
ls
# backend-leader.yaml  backend-worker.yaml  backend-service.yaml
# configmap.yaml       frontend-deployment.yaml
# ingress-nginx.yaml   ingress-clusterip.yaml
# kustomization.yaml   namespace.yaml        secret.example.yaml
```

### 4a. Pin your image registry/tag

Edit `kustomization.yaml`:

```yaml
images:
  - name: REGISTRY/parking-backend
    newName: swr.your-region.your-hcs.local/parking/parking-backend
    newTag: v1.0.0
  - name: REGISTRY/parking-frontend
    newName: swr.your-region.your-hcs.local/parking/parking-frontend
    newTag: v1.0.0
```

### 4b. Fill in the ConfigMap

`configmap.yaml` carries every **non-secret** runtime knob. Edit at minimum:

| Key | Value |
|---|---|
| `COUCHBASE_CONNECTION_STRING` | `couchbases://couchbase-prod.your-hcs.local` |
| `COUCHBASE_BUCKET` | `db_parking` |
| `OBS_ENDPOINT` | the OBS endpoint from §3 |
| `OBS_BUCKET` | the OBS bucket from §3 |
| `FIRST_ADMIN_EMAIL` | the admin login the customer wants seeded |
| `FIRST_ADMIN_COMPANY` | display name |

Leave `STORAGE_TYPE: "obs"` and `DB_TYPE: "couchbase"` alone — those are the production values.

### 4c. Create the secrets

The repo ships `secret.example.yaml` with placeholder values. **Do NOT apply it as-is**. Instead create real secrets imperatively (so they never live on disk in the repo):

```bash
kubectl apply -f deploy/k8s/namespace.yaml

# 1. Application secrets
kubectl -n parking-app create secret generic parking-backend-secrets \
    --from-literal=JWT_SECRET="$(openssl rand -hex 64)" \
    --from-literal=COUCHBASE_USERNAME="parking_app" \
    --from-literal=COUCHBASE_PASSWORD="<paste>" \
    --from-literal=FIRST_ADMIN_PASSWORD="<paste-strong>" \
    --from-literal=OBS_ACCESS_KEY="<AK>" \
    --from-literal=OBS_SECRET_KEY="<SK>" \
    --from-literal=EMERGENT_LLM_KEY="" \
    --from-literal=MONGO_URL=""

# 2. Couchbase root CA (mounted as /etc/ssl/cb-ca.pem in the pods)
kubectl -n parking-app create secret generic parking-cb-ca \
    --from-file=cb-ca.pem=./cb-ca.pem

# 3. (Option A only) TLS cert for the ingress
kubectl -n parking-app create secret tls parking-tls \
    --cert=fullchain.pem --key=privkey.pem
```

Then **remove** `secret.example.yaml` from the `kustomization.yaml` resources list — the imperative secrets above already exist.

### 4d. Choose your edge — one of:

- **Option A: Nginx Ingress + TLS termination at the cluster.** Keep `ingress-nginx.yaml` in `kustomization.yaml`. Edit the host (`parking.your-hcs.local`).
- **Option B: External HCS ELB / F5 / customer LB.** Replace `ingress-nginx.yaml` with `ingress-clusterip.yaml` in `kustomization.yaml`. Point your LB at the NodePort it exposes (default `30080`) on every cluster node.

You can apply both files (Option A AND Option B coexist), but pick one as the supported path so monitoring is unambiguous.

---

## 5. Deploy

```bash
kubectl apply -k deploy/k8s/
```

Watch it come up:

```bash
kubectl -n parking-app get pods -w
# Expect:
#   parking-backend-leader-...   1/1 Running
#   parking-backend-worker-...   1/1 Running   (× 2)
#   parking-frontend-...         1/1 Running   (× 2)
```

First-boot logs from the leader pod:

```bash
kubectl -n parking-app logs deployment/parking-backend-leader
# Expect:
#   storage backend: obs (bucket=parking-uploads)
#   Database indexes ensured
#   Default admin account created: <FIRST_ADMIN_EMAIL>
#   Background maintenance loops started on this replica
```

---

## 6. Smoke test

```bash
# Pick whichever hostname you wired up.
HOST=https://parking.your-hcs.local

curl -I $HOST/healthz
# Expect: HTTP/2 200  (frontend nginx is serving)

curl -I $HOST/api/buildings
# Expect: HTTP/2 401  (proxy works AND auth is enforced)

# Login as the seeded admin, then upload a floor layout:
TOKEN=$(curl -s -X POST $HOST/api/auth/login \
   -H "Content-Type: application/json" \
   -d '{"email":"<FIRST_ADMIN_EMAIL>","password":"<FIRST_ADMIN_PASSWORD>"}' \
 | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# (Get a floor_id from the UI or /api/buildings, then:)
curl -X POST $HOST/api/floors/$FLOOR_ID/layout \
   -H "Authorization: Bearer $TOKEN" \
   -F "file=@./test.png;type=image/png"
# Expect: 200 + {"layout_image_url":"/api/uploads/floor_<id>.png"}
```

If the upload returns 200 and the image renders in the admin UI, OBS is wired correctly.

---

## 7. Why two backend Deployments?

This is the most-asked question on review:

- `parking-backend-leader` — `replicas: 1`, `RUN_BACKGROUND_TASKS=true`. Runs the periodic loops (auto-mark-no-shows, waitlist-expiry, slot-release).
- `parking-backend-worker` — `replicas: N`, `RUN_BACKGROUND_TASKS=false`. Pure API traffic.

Both Deployments share the same Service (`backend:8001`) so the load balancer doesn't care which pod answers an API call. We just guarantee that the timer-driven loops execute on **exactly one pod** to avoid duplicate "no-show" emails and similar.

If the leader pod dies, Kubernetes restarts it within seconds (the Deployment uses `strategy: Recreate` to make sure two leaders never coexist during a rollout). During those seconds the periodic loops simply don't run — which is fine, they're idempotent and will catch up on the next tick.

---

## 8. Scaling

The worker Deployment ships with an HPA targeting 70% CPU / 75% memory (see `backend-worker.yaml`). Tune via:

```bash
kubectl -n parking-app edit hpa parking-backend-worker
```

Frontend pods can be scaled with a plain `kubectl scale`:

```bash
kubectl -n parking-app scale deployment/parking-frontend --replicas=4
```

The leader stays at 1 — don't change that.

---

## 9. Rolling out a new version

```bash
# Build & push the new tag (steps in §2)

# Then on the Ops workstation:
cd parking-app/deploy/k8s
kustomize edit set image \
   REGISTRY/parking-backend=swr.your-region.your-hcs.local/parking/parking-backend:v1.1.0 \
   REGISTRY/parking-frontend=swr.your-region.your-hcs.local/parking/parking-frontend:v1.1.0
kubectl apply -k .
kubectl -n parking-app rollout status deployment/parking-backend-worker
kubectl -n parking-app rollout status deployment/parking-backend-leader
kubectl -n parking-app rollout status deployment/parking-frontend
```

Rollback on a bad release:

```bash
kubectl -n parking-app rollout undo deployment/parking-backend-worker
kubectl -n parking-app rollout undo deployment/parking-backend-leader
kubectl -n parking-app rollout undo deployment/parking-frontend
```

---

## 10. Backups & DR

- **Couchbase**: backed up by the customer's existing `cbbackupmgr` schedule. Nothing app-side to do.
- **OBS bucket**: enable bucket versioning + lifecycle (move to Cold after 90 days, delete-marker retention 30 days). Floor-layout images are non-critical (admins can re-upload), so a simple lifecycle policy is sufficient.
- **Kubernetes manifests**: keep `deploy/k8s/` under your customer's GitOps / config-management of choice. The `secret.yaml` should NEVER be committed; the imperative `kubectl create secret` in §4c is the source of truth.

---

## 11. Day-2 reference

```bash
# Logs (all three deployments tagged with app.kubernetes.io/name)
kubectl -n parking-app logs -l app.kubernetes.io/name=parking-backend --tail=200 -f
kubectl -n parking-app logs deployment/parking-backend-leader -f
kubectl -n parking-app logs deployment/parking-frontend --tail=100

# Pod status / events
kubectl -n parking-app get pods
kubectl -n parking-app describe pod <pod-name>

# Restart a deployment (e.g. after editing the ConfigMap)
kubectl -n parking-app rollout restart deployment/parking-backend-leader
kubectl -n parking-app rollout restart deployment/parking-backend-worker

# Ad-hoc maintenance: run a one-shot script inside the leader pod
kubectl -n parking-app exec -it deployment/parking-backend-leader -- \
   python scripts/db_cleanup.py --dry-run
```

---

## 12. Optional features (enable / disable)

The app ships one optional, internet-dependent feature behind a runtime flag so the customer's Ops team can flip it without rebuilding images.

### AI Insights (LLM-powered analytics on the Reports page)

- **What it does** — the admin Reports page has an "Generate Insights" button that POSTs to `/api/reports/ai-insights`. The backend summarises live parking data, sends the summary to an LLM (via Emergent's universal-key broker → OpenAI/Anthropic/Gemini), and renders the natural-language response. Uses no other resources; does not affect bookings, attendants, or any other flow.
- **Network impact** — the backend pod opens an HTTPS connection to the Emergent LLM endpoint (public internet). All other features stay fully on-prem.
- **Single switch** — `AI_INSIGHTS_ENABLED` (in `parking-backend-config` ConfigMap). Tri-state:
  - `"true"` → force on. The endpoint will run; if `EMERGENT_LLM_KEY` is empty it will fail at request time with a clear error.
  - `"false"` → force off. The admin UI hides the AI Insights button on the Dashboard and the AI section on Reports. The backend returns `503 AI Insights are disabled in this deployment.` if anyone hits the endpoint anyway.
  - empty / unset (default) → **auto** — enabled iff `EMERGENT_LLM_KEY` in the Secret is non-empty.

### Recommended posture per deployment

| Customer posture | `EMERGENT_LLM_KEY` | `AI_INSIGHTS_ENABLED` | UI shown? |
|---|---|---|---|
| Air-gapped / no public-internet egress | empty | `"false"` | ❌ |
| HCS with controlled egress, AI not yet approved | empty | (unset) | ❌ |
| HCS with controlled egress, AI approved | `<real key>` | (unset) | ✅ |
| Demo / dev | `<real key>` | `"true"` | ✅ |

### Flipping the switch live

```bash
# Disable
kubectl -n parking-app patch configmap parking-backend-config \
   --type merge -p '{"data":{"AI_INSIGHTS_ENABLED":"false"}}'
kubectl -n parking-app rollout restart deployment/parking-backend-leader \
                                       deployment/parking-backend-worker

# Re-enable (auto-detect via Secret)
kubectl -n parking-app patch configmap parking-backend-config \
   --type merge -p '{"data":{"AI_INSIGHTS_ENABLED":""}}'
kubectl -n parking-app rollout restart deployment/parking-backend-leader \
                                       deployment/parking-backend-worker
```

The frontend reads the live state from the public `GET /api/system/features` endpoint at SPA load time — so a hard refresh (or new tab) after the rollout is enough; no frontend rebuild required.

### If you need to remove the package entirely

For deployments where even **shipping** the LLM SDK is unacceptable: edit `backend/Dockerfile`, drop the `pip install emergentintegrations ...` line, and rebuild. The backend will boot fine — the import is lazy (inside the route handler) — and the gate above will keep the endpoint hidden as long as `AI_INSIGHTS_ENABLED=false` is set.

### Parking-attendant flow vs. self-check-in

| ConfigMap key | Default | Effect |
|---|---|---|
| `ATTENDANT_MODE_ENABLED` | `"true"` | On-site attendants confirm arrivals / report no-shows via the Attendant Dashboard. Original flow. |
| `ATTENDANT_MODE_ENABLED` | `"false"` | No attendants. Parkers tap a **"Check in"** button on their reservation between `start_time` and `start_time + SELF_CHECKIN_WINDOW_MINUTES`. If they miss the window, the auto-no-show loop immediately marks the reservation as no-show, releases the slot, and notifies the next person on the building's waitlist. |
| `SELF_CHECKIN_WINDOW_MINUTES` | `"15"` | Clamped to 5–240. Only consulted when `ATTENDANT_MODE_ENABLED=false`. |

The flag is read live by both backend and frontend (via `GET /api/system/features`) — a hard refresh after a ConfigMap change is enough; no image rebuild needed. Flipping it for the cluster:

```bash
kubectl -n parking-app patch configmap parking-backend-config \
  --type merge -p '{"data":{"ATTENDANT_MODE_ENABLED":"false","SELF_CHECKIN_WINDOW_MINUTES":"15"}}'
kubectl -n parking-app rollout restart deployment/parking-backend-leader \
                                       deployment/parking-backend-worker
```

In self-check-in mode the background no-show loop runs every **60 s** (vs. 300 s in attendant mode) so a missed check-in clears the waitlist within a minute.

---

## 13. Common issues

### 13.1 Runtime (cluster) issues

| Symptom | Likely cause | Fix |
|---|---|---|
| Pods CrashLoopBackOff with `OBS endpoint unreachable` | OBS endpoint typo, or NetworkPolicy blocking egress | `kubectl -n parking-app exec ... -- curl -v $OBS_ENDPOINT` from inside a pod. |
| `couchbase.exceptions.UnAmbiguousTimeoutException` on startup | Cluster firewall blocks 11207 from CCE, or wrong root CA | Confirm `cb-ca.pem` matches the cluster's current cert; `nc -vz couchbase 11207`. |
| Two "no-show" emails for the same reservation | Background loops running on >1 pod | Check `kubectl -n parking-app describe deployment/parking-backend-leader` — `RUN_BACKGROUND_TASKS=true` must appear ONLY there. |
| Floor-layout uploads return 200 but image doesn't display | Frontend cached the old (404) URL | Hard-refresh; check `kubectl -n parking-app logs deployment/parking-backend-leader \| grep "/api/uploads"`. |
| `403 Signature does not match` from OBS | AK/SK has wrong region or AddressingStyle | Already handled by the adapter (path-style + s3v4). Re-check the AK/SK pair. |

### 13.2 Build-host / image-push issues

These are bumps you'll likely hit on the laptop or CI runner that runs `./scripts/build_and_push_images.sh`. They don't affect the cluster but they will block a release.

#### a. `dial unix /Users/.../docker.sock: no such file or directory`

The Docker daemon isn't running on the build host. Start Docker Desktop (`open -a Docker`) and wait ~20 s for the whale icon to settle. Verify with `docker info`. Alternatives if you don't want Docker Desktop: `colima start` or Rancher Desktop.

#### b. `frontend/yarn.lock: not found` during build

The repo doesn't track `frontend/yarn.lock`. Generate it once on the build host before the first build:

```bash
cd frontend && yarn install && cd ..
```

Then commit it to the repo so the next person doesn't hit this:

```bash
git add frontend/yarn.lock
git commit -m "chore(frontend): commit yarn.lock for reproducible Docker builds"
```

#### c. `Could not find a version that satisfies the requirement emergentintegrations==0.1.0`

`emergentintegrations` is published to a private CloudFront index, not public PyPI. It must NOT appear in `backend/requirements.txt` — only in the dedicated `pip install` line in `backend/Dockerfile` that supplies `--extra-index-url`. If a stray `pip freeze` reintroduces it into `requirements.txt`, drop the line.

#### d. Image built on Apple Silicon (ARM64), CCE nodes fail with `exec format error`

`docker buildx build --platform linux/amd64 ...` — CCE worker nodes are almost always x86_64 unless explicitly provisioned for ARM. Either run `./scripts/build_and_push_images.sh` from an x86 build host, or update the script to default to `--platform linux/amd64`.

#### e. `tls: failed to verify certificate: x509: certificate is not valid for any names` against SWR ⚠️ **must be fixed server-side**

The SWR endpoint at `swr.<region>.<customer-domain>` may present an internal Huawei placeholder cert (`CN=BasicService-CloudNginx`, no SAN extension). `docker login` with the legacy daemon's `insecure-registries` flag can paper over it; `docker push` (which uses containerd's pusher) will still fail. **The CCE worker nodes will fail the same way at image-pull time** — so this is a deployment blocker, not just a developer-laptop annoyance.

**Diagnose:**

```bash
openssl s_client -connect swr.<region>.<customer-domain>:443 \
  -servername swr.<region>.<customer-domain> </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -ext subjectAltName
```

If `subject = CN=BasicService-CloudNginx` and / or no SAN extension is present, the cert is wrong.

**Permanent fix (on the SWR / HCS side — file a ticket with HCS Ops):** bind a service cert to the SWR project endpoint with:
- `CN = swr.<region>.<customer-domain>`
- `SAN: DNS:swr.<region>.<customer-domain>, DNS:*.swr.<region>.<customer-domain>`
- Signed by an internal CA already trusted on the customer's hosts (corporate root, or a CA distributed by MDM / cloud-init).

After Ops applies the fix, the openssl command above should show your hostname under `subject` and `Subject Alternative Name`.

**Temporary workaround on the build host (Docker Desktop, macOS):**

```bash
mkdir -p ~/.docker/certs.d/swr.<region>.<customer-domain>
cat > ~/.docker/certs.d/swr.<region>.<customer-domain>/hosts.toml <<'EOF'
server = "https://swr.<region>.<customer-domain>"
[host."https://swr.<region>.<customer-domain>"]
  capabilities = ["pull", "resolve", "push"]
  skip_verify = true
EOF
```

Then in **Docker Desktop → Settings → General**, uncheck **"Use containerd for pulling and storing images"** for the duration of the push (legacy daemon honours `insecure-registries` more reliably than the containerd image store). Re-enable after the push succeeds.

**Temporary workaround on the CCE nodes** (only until the cert is fixed): drop `/etc/containerd/certs.d/swr.<region>.<customer-domain>/hosts.toml` with the same contents on every worker via cloud-init / DaemonSet. **Do not leave this in production** — it disables certificate validation against the registry.

> ⚠️ Avoid trusting `Huawei Cloud CA` system-wide on developer Macs to "fix" this. It would make the laptop trust every certificate that bogus CA signs across the entire HCS estate — large blast radius for a problem that is one Ops ticket away from being fixed properly.

#### f. SWR push error: `request returned 500 Internal Server Error ... /v1.54/auth`

Stale `osxkeychain` credential helper on the build host. Edit `~/.docker/config.json`, remove the `"credsStore"` line, restart Docker Desktop, retry `docker login` with `--password-stdin` (never `-p` — credentials end up in shell history).

---

