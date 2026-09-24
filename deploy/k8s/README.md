# Kubernetes (CCE) Manifests — Parking Reservation

These YAMLs deploy the app to a Huawei CCE cluster (or any vanilla Kubernetes ≥ 1.25) with OBS as the file-storage backend. Full step-by-step deployment instructions live in [`/app/docs/ONPREM_HCS_CCE_RUNBOOK.md`](../../docs/ONPREM_HCS_CCE_RUNBOOK.md).

## Layout

| File | Purpose |
|---|---|
| `namespace.yaml` | The `parking-app` namespace. Apply first. |
| `configmap.yaml` | All non-secret env vars (Couchbase host, OBS endpoint, JWT algo, etc.). |
| `secret.example.yaml` | **Template** for the secrets used by backend pods + Couchbase root CA. **Do not commit real values.** Create the live secrets with `kubectl create secret` instead — see the runbook §4c. |
| `backend-leader.yaml` | Single-replica Deployment with `RUN_BACKGROUND_TASKS=true`. Owns the periodic timers. `strategy: Recreate`. |
| `backend-worker.yaml` | Multi-replica Deployment with `RUN_BACKGROUND_TASKS=false` + HPA. Pure API traffic. |
| `backend-service.yaml` | Single ClusterIP Service named `backend` fronting both leader and worker pods. |
| `frontend-deployment.yaml` | Nginx + React SPA Deployment + ClusterIP Service. |
| `ingress-nginx.yaml` | **Edge option A** — Nginx Ingress + TLS Secret (`parking-tls`). |
| `ingress-clusterip.yaml` | **Edge option B** — NodePort Service when an external HCS ELB / F5 fronts the cluster. |
| `kustomization.yaml` | `kubectl apply -k .` entry point. Pin image tags here. |

## Quick start

```bash
# 1. Apply the namespace
kubectl apply -f namespace.yaml

# 2. Create the real secrets (see runbook §4c) — DO NOT apply secret.example.yaml
kubectl -n parking-app create secret generic parking-backend-secrets \
    --from-literal=JWT_SECRET="$(openssl rand -hex 64)" \
    --from-literal=COUCHBASE_USERNAME="..." \
    --from-literal=COUCHBASE_PASSWORD="..." \
    --from-literal=FIRST_ADMIN_PASSWORD="..." \
    --from-literal=OBS_ACCESS_KEY="..." \
    --from-literal=OBS_SECRET_KEY="..." \
    --from-literal=EMERGENT_LLM_KEY="" \
    --from-literal=MONGO_URL=""

kubectl -n parking-app create secret generic parking-cb-ca \
    --from-file=cb-ca.pem=/path/to/cb-ca.pem

# (Option A only) TLS for the ingress
kubectl -n parking-app create secret tls parking-tls \
    --cert=/path/to/fullchain.pem --key=/path/to/privkey.pem

# 3. Edit configmap.yaml + kustomization.yaml for your environment.
#    Then remove `secret.example.yaml` from the resources list in kustomization.yaml.

# 4. Apply the rest
kubectl apply -k .

# 5. Watch it come up
kubectl -n parking-app get pods -w
```

## Switching the edge option

`kustomization.yaml` ships with `ingress-nginx.yaml` enabled. To switch to the NodePort variant:

```yaml
# kustomization.yaml
resources:
  - namespace.yaml
  - configmap.yaml
  - backend-leader.yaml
  - backend-worker.yaml
  - backend-service.yaml
  - frontend-deployment.yaml
  - ingress-clusterip.yaml   # was: ingress-nginx.yaml
```

Both options are documented in the runbook §4d.
