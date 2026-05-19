# Scoring Pipeline

Hourly anomaly scoring service for the Hadar project. Loads promoted Isolation Forest models and scores recent temperature readings, persisting anomaly events to PostgreSQL.

## What It Does

1. Reads the promoted model marker (`promoted_model.json`) from shared storage.
2. Loads the corresponding per-device Isolation Forest models.
3. Fetches recent temperature readings from PostgreSQL.
4. Scores readings and upserts anomaly events (with severity and status) into the `anomaly_events` table.
5. Runs once at startup, then repeats on an hourly schedule.

## Runtime

The scoring pipeline runs as a container alongside the isolation-forest trainer in the combined `hadar-app` Kubernetes deployment. Both containers share a persistent volume at `/mnt/hadar-model-data` for model artifacts.

## Configuration

Environment variables (non-secret values set via ConfigMap, credentials via Secret):

| Variable | Description |
|---|---|
| `DB_DRIVER` | SQLAlchemy driver (default `postgresql+asyncpg`) |
| `DB_HOST` | PostgreSQL host |
| `DB_PORT` | PostgreSQL port |
| `DB_NAME` | Database name |
| `DB_USER` | Database user (from Secret) |
| `DB_PASSWORD` | Database password (from Secret) |
| `PERSIST_ANOMALY_EVENTS` | Set to `true` to write anomaly events (default `false`) |
| `PROMOTION_MARKER_PATH` | Path to `promoted_model.json` on the shared volume |
