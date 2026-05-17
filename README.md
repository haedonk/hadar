# Hadar

Hadar is a smart home monitoring project for ingesting Zigbee/MQTT sensor events into PostgreSQL and running scheduled anomaly detection over the collected data.

## Components

- `api/`: FastAPI backend for the Hadar dashboard.
- `ui/`: Vite + React dashboard SPA served via nginx.
- `ingestion-pipeline/`: MQTT consumer and processor for energy and temperature events.
- `isolation-forest/`: scheduled anomaly detection / model training pipeline.
- `scoring-pipeline/`: hourly scoring service that persists anomaly events.
- `db/`: shared SQLAlchemy database models and session setup.
- `docs/`: architecture diagram and database schema notes.
- `k3s/`: sanitized Kubernetes manifests for the `hadar` k3s deployment.

## Architecture

![Hadar architecture diagram](images/architecture-diagram.png)

## Local Setup

Create one Python environment at the repository root and install the shared local dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -r requirements.txt
```

Service-specific runtime dependency files are still kept for Docker builds and deployable service boundaries:

```text
api/requirements.txt
ingestion-pipeline/requirements.txt
isolation-forest/requirements.txt
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
docker build -f scoring-pipeline/Dockerfile -t haka9670/scoring-pipeline:latest .
docker build -f api/Dockerfile -t haka9670/hadar-api:latest .
docker build -f ui/Dockerfile -t haka9670/hadar-ui:latest ui
```

Prefer immutable commit-SHA tags over `latest` for production rollouts (the
isolation-forest and scoring-pipeline images are pinned this way in `k3s/`).

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

Run static type checks on the shared database package:

```bash
mypy db
```

Run tests where present:

```bash
pytest
```
