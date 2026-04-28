# Hadar

Hadar is a smart home monitoring project for ingesting Zigbee/MQTT sensor events into PostgreSQL and running scheduled anomaly detection over the collected data.

## Components

- `ingestion-pipeline/`: MQTT consumer and processor for energy and temperature events.
- `isolation-forest/`: scheduled anomaly detection pipeline.
- `db/`: shared SQLAlchemy database models and session setup.
- `docs/`: database schema notes.
- `k3s/`: sanitized Kubernetes manifests for the `hadar` k3s deployment.

## Local Setup

Create a Python environment and install development dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Each service has its own runtime dependencies:

```bash
pip install -r ingestion-pipeline/requirements.txt
pip install -r isolation-forest/requirements.txt
```

Copy the example environment files and fill in local values:

```bash
cp ingestion-pipeline/.env.example ingestion-pipeline/.env
cp isolation-forest/.env.example isolation-forest/.env
```

Do not commit `.env` files or real credentials.

## Docker Images

Build from the repository root so the shared `db/` package is included:

```bash
docker build -f ingestion-pipeline/Dockerfile -t haka9670/ingestion-pipeline:latest .
docker build -f isolation-forest/Dockerfile -t haka9670/isolation-forest:latest .
```

## k3s Deployment

Deployment manifests live in `k3s/`. They intentionally exclude real secrets. See `k3s/README.md` for apply order, required secret keys, and verification commands.

Before deploying to a new environment:

- Set the target MQTT broker host in `k3s/ingestion-pipeline/configmap.yaml`.
- Create Kubernetes Secrets from local credentials.
- Confirm PostgreSQL and MQTT are reachable from the cluster.
- Rotate any credentials that were ever exposed outside a secret manager.

## Checks

Run linting from the repository root:

```bash
ruff check .
```

Run tests where present:

```bash
pytest
```

