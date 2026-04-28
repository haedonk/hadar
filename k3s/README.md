# Hadar k3s Deployment

These manifests describe the `hadar` namespace workloads currently used by the project.

## Files

- `namespace.yaml`: creates the `hadar` namespace.
- `storage.yaml`: creates the retained hostPath PV and bound PVC.
- `ingestion-pipeline/configmap.yaml`: non-secret ingestion settings.
- `ingestion-pipeline/deployment.yaml`: MQTT-to-PostgreSQL ingestion worker.
- `ingestion-pipeline/secret.example.yaml`: placeholder secret shape only.
- `isolation-forest/configmap.yaml`: non-secret isolation forest settings.
- `isolation-forest/cronjob.yaml`: scheduled anomaly detection job.
- `isolation-forest/secret.example.yaml`: placeholder secret shape only.

## Required External Services

- PostgreSQL service reachable at `postgres.db.svc.cluster.local:5432`.
- MQTT broker reachable from inside the cluster.
- Host path `/mnt/truenas-hadar` available on the k3s node that binds `hadar-truenas-pv`.
- Docker images:
  - `haka9670/ingestion-pipeline:latest`
  - `haka9670/isolation-forest:latest`

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
```

## Apply Order

```bash
kubectl apply -f k3s/namespace.yaml
kubectl apply -f k3s/storage.yaml
kubectl apply -f k3s/ingestion-pipeline/configmap.yaml
kubectl apply -f k3s/isolation-forest/configmap.yaml
kubectl apply -f k3s/ingestion-pipeline/deployment.yaml
kubectl apply -f k3s/isolation-forest/cronjob.yaml
```

## Verify

```bash
kubectl -n hadar rollout status deployment/ingestion-pipeline
kubectl -n hadar get cronjob isolation-forest
kubectl -n hadar get pods
```

