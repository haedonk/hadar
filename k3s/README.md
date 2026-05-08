# Hadar k3s Deployment

These manifests describe the `hadar` namespace workloads currently used by the project.

## Files

- `namespace.yaml`: creates the `hadar` namespace.
- `storage.yaml`: creates the retained hostPath PV and bound PVC.
- `ingestion-pipeline/configmap.yaml`: non-secret ingestion settings.
- `ingestion-pipeline/deployment.yaml`: MQTT-to-PostgreSQL ingestion worker.
- `ingestion-pipeline/secret.example.yaml`: placeholder secret shape only.
- `isolation-forest/configmap.yaml`: non-secret isolation forest settings.
- `isolation-forest/deployment.yaml`: long-running APScheduler service for training sweeps.
- `isolation-forest/secret.example.yaml`: placeholder secret shape only.
- `scoring-pipeline/configmap.yaml`: non-secret hourly scoring settings, including the promotion marker path and disabled-by-default anomaly event persistence kill switch.
- `scoring-pipeline/deployment.yaml`: standalone service that exports recent readings on startup and hourly; reuses `isolation-forest-creds` for DB credentials.
- `scoring-pipeline/secret.example.yaml`: placeholder secret shape only.

## Required External Services

- PostgreSQL service reachable at `postgres.db.svc.cluster.local:5432`.
- MQTT broker reachable from inside the cluster.
- Host path `/mnt/truenas-hadar` available on the k3s node that binds `hadar-truenas-pv`.
- Docker images:
  - `haka9670/ingestion-pipeline:latest`
  - `haka9670/isolation-forest:latest`
  - `haka9670/scoring-pipeline:latest`

The scoring and isolation-forest manifests use `imagePullPolicy: IfNotPresent`; rebuild or preload new image tags before rollout, and prefer immutable tags over `latest` for production deploys.

## Before Applying

Set `MQTT_HOST` in `ingestion-pipeline/configmap.yaml` for the target environment.

Create real secrets from local values. Do not commit real secret manifests.

```bash
kubectl create secret generic ingestion-pipeline-creds \
  -n hadar \
  --from-literal=DATABASE_URL='postgresql+asyncpg://USER:PASSWORD@postgres.db.svc.cluster.local:5432/zigbee_db' \
  --from-literal=MQTT_USER='USERNAME' \
  --from-literal=MQTT_PASS='PASSWORD'

kubectl create secret generic isolation-forest-creds \
  -n hadar \
  --from-literal=DB_USER='USERNAME' \
  --from-literal=DB_PASSWORD='PASSWORD'

# scoring-pipeline currently reuses isolation-forest-creds because it needs the same PostgreSQL DB_USER/DB_PASSWORD.
```

## Apply Order

```bash
kubectl apply -f k3s/namespace.yaml
kubectl apply -f k3s/storage.yaml
kubectl apply -f k3s/ingestion-pipeline/configmap.yaml
kubectl apply -f k3s/isolation-forest/configmap.yaml
kubectl apply -f k3s/scoring-pipeline/configmap.yaml
kubectl apply -f k3s/ingestion-pipeline/deployment.yaml
kubectl apply -f k3s/isolation-forest/deployment.yaml
kubectl apply -f k3s/scoring-pipeline/deployment.yaml
```

## Verify

```bash
kubectl -n hadar rollout status deployment/ingestion-pipeline
kubectl -n hadar rollout status deployment/isolation-forest
kubectl -n hadar rollout status deployment/scoring-pipeline
kubectl -n hadar get pods
```
