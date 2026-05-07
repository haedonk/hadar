# Scoring Pipeline

Separate downstream service for HADAR anomaly scoring dry runs.

Initial scope:

- Read recent temperature readings from PostgreSQL.
- Export hourly dry-run CSV files.
- Run once on service startup and then on an hourly schedule.
- Keep ingestion, training, FastAPI, and dashboard services unchanged.

Planned output path inside the container:

```text
/mnt/hadar-data/output/hourly-scoring-runs/
```

Mounted host path:

```text
/mnt/nas/hadar/scoring-pipeline/output/hourly-scoring-runs/
```

This service does not write `anomaly_events` yet.

Model artifacts are read from:

```text
/mnt/hadar-model-data/output/training-sweeps/20260506T220024Z_comprehensive-training-sweep/configs/full_c003_e100/models
```
