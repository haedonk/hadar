# Plan: Frontend Implementation - 2026-05-08

## Current State

HADAR is currently backend-only in this repository. The active services are:

- `ingestion-pipeline/`: MQTT-to-PostgreSQL ingestion worker.
- `isolation-forest/`: scheduled training/sweep service that promotes a model
  by writing `promoted_model.json`.
- `scoring-pipeline/`: hourly scoring service that exports CSVs and, behind
  `ENABLE_ANOMALY_EVENT_PERSISTENCE`, writes anomaly rows to
  `anomaly_events`.
- `db/`: shared SQLAlchemy models, including the new `AnomalyEvent` model.
- `k3s/`: current cluster manifests for each backend worker.

There is no frontend directory, FastAPI service, HTTP API, or dashboard code in
the repo yet. The scoring README still says FastAPI and dashboard services are
unchanged, so the first frontend implementation batch should include an API
foundation before building a browser dashboard.

The Trello-informed active work is the post-promotion scoring deploy:

- validate Claude's promotion/persistence batch locally;
- deploy with anomaly persistence disabled first;
- verify CSV output, promotion marker reads, and z-score stats;
- run a training sweep that writes `promoted_model.json`;
- enable anomaly persistence and verify `anomaly_events` idempotency.

The frontend should begin after, or in parallel with, the API-contract work for
`anomaly_events`. It should not depend on reading CSV files from the PVC as its
primary data path.

## Product Goal

Build an operator dashboard for home sensor anomaly monitoring:

- show whether ingestion, training, scoring, and model promotion are healthy;
- surface open anomaly events with enough context to triage quickly;
- let an operator acknowledge, resolve, and severity-tag events;
- show device-level history and recent temperature/energy behavior;
- make model provenance visible so anomalies can be traced to a promoted model
  run/config.

The first usable screen should be an operational dashboard, not a marketing
landing page.

## Proposed App Stack

Because the repo is Python-first and already uses async SQLAlchemy, add a small
FastAPI service plus a Vite React frontend:

- Backend API: `FastAPI`, `uvicorn`, `pydantic`, existing async SQLAlchemy
  session helpers from `db/`.
- Frontend: `React`, `TypeScript`, `Vite`.
- Routing/state: `React Router` plus `TanStack Query` for API state.
- Charts: `Recharts` or `visx`; prefer `Recharts` for the first iteration
  unless there is a need for heavier custom visualization.
- Tables: start with native table components and small helpers; add TanStack
  Table only if sorting/filtering complexity grows.
- Styling: simple app-local CSS or Tailwind if the repo already standardizes
  on it during scaffolding. Keep the UI dense and operational, with restrained
  colors and compact controls.

Proposed directories:

```text
api/
  main.py
  routers/
  schemas/
  services/
frontend/
  package.json
  src/
```

If deployment consolidation happens first, these can become additional
containers in the shared HADAR pod. If not, API and frontend can initially be
separate k3s workloads and later folded into the unified deployment.

## Backend API Dependencies

The frontend needs an HTTP API before it can be useful. Minimum endpoints:

### Health And Runtime

- `GET /healthz`
  - returns process/database health for the API service.
- `GET /api/system/status`
  - ingestion last event timestamp;
  - latest scoring tick timestamp;
  - latest training sweep run;
  - current promoted model marker summary;
  - whether anomaly persistence is enabled in the scoring deployment if that
    can be exposed safely.

The status endpoint may start with DB-derived values and later add Kubernetes
metadata if a service account/RBAC plan is approved.

### Devices

- `GET /api/devices`
  - returns device id, label, type, description, current load group, last seen
    temperature timestamp, last seen energy timestamp, and latest values.
- `GET /api/devices/{device_id}`
  - returns device metadata and recent summary stats.
- `GET /api/devices/{device_id}/readings`
  - query params: `from`, `to`, `metric=temperature|energy`, `limit`.
  - returns chart-ready time series.

### Anomaly Events

- `GET /api/anomaly-events`
  - query params: `status`, `severity`, `device_id`, `model_run_id`, `from`,
    `to`, `limit`, `cursor` or `offset`.
  - default filter should prioritize `status=open`, newest first.
- `GET /api/anomaly-events/{id}`
  - returns one event with device metadata and the linked temperature reading.
- `PATCH /api/anomaly-events/{id}`
  - updates operator-owned fields only:
    - `event_status`: `open | acknowledged | resolved`
    - `event_severity`: `low | medium | high | null`
  - must not allow edits to model/scoring fields.
- `POST /api/anomaly-events/bulk-status`
  - optional after single-event updates work.

### Model Promotion

- `GET /api/models/promoted`
  - reads the promoted model marker and returns:
    - `run_id`
    - `config_name`
    - `promoted_at`
    - `schema_version`
    - artifact path existence/status
- `GET /api/models/runs`
  - optional second phase; can list known run/config rows from artifacts or a
    future model registry table.

## Initial Data Contracts

Use JSON field names aligned with database/model names to reduce translation
cost.

### `AnomalyEventSummary`

```json
{
  "id": 123,
  "temperature_reading_id": 456,
  "device_id": "uuid",
  "device_label": "living_room_sensor",
  "model_run_id": "20260506T220024Z_comprehensive-training-sweep",
  "model_config_name": "full_c003_e100",
  "model_trained_at": "2026-05-06T22:00:24Z",
  "scored_at": "2026-05-08T14:00:00Z",
  "prediction": -1,
  "anomaly_score": -0.1734,
  "anomaly_reason": "temperature_zscore exceeded trained profile",
  "event_status": "open",
  "event_severity": "medium",
  "temperature": 82.4,
  "reading_ts": "2026-05-08T13:56:12Z",
  "created_at": "2026-05-08T14:00:04Z",
  "updated_at": "2026-05-08T14:00:04Z"
}
```

### `DeviceSummary`

```json
{
  "id": "uuid",
  "device_label": "living_room_sensor",
  "device_type": "plug",
  "description": "",
  "last_temperature_ts": "2026-05-08T13:56:12Z",
  "last_temperature": 72.1,
  "last_energy_ts": "2026-05-08T13:56:10Z",
  "last_power_watts": 42.5,
  "open_anomaly_count": 3
}
```

### `SystemStatus`

```json
{
  "database": "ok",
  "ingestion_last_seen_at": "2026-05-08T13:56:12Z",
  "scoring_last_scored_at": "2026-05-08T14:00:00Z",
  "open_anomaly_count": 12,
  "promoted_model": {
    "run_id": "20260506T220024Z_comprehensive-training-sweep",
    "config_name": "full_c003_e100",
    "promoted_at": "2026-05-08T12:10:00Z",
    "schema_version": 1
  }
}
```

## Dashboard Views

### 1. Operations Overview

First screen. Dense status view with:

- service health strip for ingestion, training, scoring, API;
- open anomaly count and trend;
- latest scoring tick and latest ingested reading;
- promoted model run/config;
- top devices by open anomaly count;
- recent anomalies table.

### 2. Anomaly Queue

Primary triage workflow:

- filter by status, severity, device, model run, and time window;
- sortable table by scored time, score, severity, device;
- row actions for acknowledge, resolve, and severity assignment;
- detail drawer with linked reading, surrounding time-series context, and model
  provenance.

### 3. Device Detail

Device-centric investigation:

- latest readings and health;
- temperature/energy time-series chart;
- anomaly overlay markers;
- open/resolved anomaly history for the device;
- rename/load-group context if available from existing DB tables.

### 4. Models And Scoring

Model provenance and deploy confidence:

- promoted marker details;
- current fallback env model fields if the API can expose them safely;
- recent model runs/configs when a model registry or artifact index exists;
- scoring run history once it is persisted beyond CSV files.

### 5. Data Quality

Later phase:

- devices with stale readings;
- devices skipped by scoring due to missing artifacts or missing metadata stats;
- ingestion errors from `error_logs`;
- linkquality/battery issues for temperature devices.

## Implementation Phases

### Phase 0 - Confirm Deploy Baseline

Prerequisites:

- `anomaly_events` table exists in PostgreSQL.
- Scoring deploy has been smoked with persistence disabled.
- Training sweep writes `promoted_model.json`.
- Persistence smoke confirms rows are written and UPSERT behavior preserves
  `event_status` and `event_severity`.

Acceptance criteria:

- There is real anomaly data to query, or a seed fixture is approved for local
  frontend development.
- The API contract below is not guessing about table names or status values.

### Phase 1 - API Skeleton

Tasks:

- Add `api/` service with FastAPI app, health endpoint, DB session wiring, and
  CORS configured for local frontend development.
- Add read-only endpoints for devices, anomaly event list/detail, and promoted
  model marker.
- Add focused tests for query shape and serialization.
- Add Dockerfile and k3s draft manifest or compose/local run notes.

Acceptance criteria:

- `GET /healthz` works locally.
- `GET /api/anomaly-events` returns joined device/reading context.
- `GET /api/devices` returns latest reading summaries.
- API responses contain no secrets or raw connection strings.

### Phase 2 - Operator Mutations

Tasks:

- Add `PATCH /api/anomaly-events/{id}` for `event_status` and
  `event_severity`.
- Validate enum values server-side.
- Confirm scoring reruns do not overwrite these fields.
- Add audit fields later if needed; do not block the first UI on audit tables.

Acceptance criteria:

- Status/severity updates persist.
- Invalid status/severity values return 422 or 400.
- Re-running scoring leaves operator-owned fields intact.

### Phase 3 - Frontend Scaffold

Tasks:

- Create `frontend/` with Vite React TypeScript.
- Add API client, query hooks, route shell, and responsive app layout.
- Implement the Operations Overview using real API data.
- Add loading, empty, and error states.

Acceptance criteria:

- `npm run dev` starts the app locally.
- The first route shows system status and recent anomalies from the API.
- Empty DB states render intentionally instead of crashing.

### Phase 4 - Anomaly Triage Workflow

Tasks:

- Build Anomaly Queue table with filters and sorting.
- Add detail drawer/panel with linked device and reading context.
- Add acknowledge/resolve/severity controls.
- Use optimistic updates only after the mutation path is reliable; otherwise
  refetch after mutation.

Acceptance criteria:

- An operator can find open anomalies, inspect context, set severity,
  acknowledge, and resolve.
- Table filters map directly to API query params.
- Mutations are reflected after refresh.

### Phase 5 - Device Investigation

Tasks:

- Build device list and device detail routes.
- Add time-series charts for temperature and energy readings.
- Overlay anomaly events on charts.
- Show stale-device and missing-data states.

Acceptance criteria:

- A user can move from an anomaly to the device detail page.
- Charts support at least 24-hour and 7-day windows.
- The selected time window is represented in API calls, not only filtered in
  the browser.

### Phase 6 - Deployment Integration

Tasks:

- Add frontend and API image builds.
- Add k3s manifests or update the planned consolidated HADAR deployment to
  include API/frontend containers.
- Configure runtime API base URL.
- Add readiness/liveness probes for the API and frontend.

Acceptance criteria:

- Dashboard is reachable inside the target network.
- API cannot expose secrets through config/status responses.
- Deployment notes document image tags and environment variables.

## API Query Notes

Initial anomaly event query should join:

- `anomaly_events.temperature_reading_id -> temperature_readings.id`
- `anomaly_events.device_id -> devices.id`

Default sort:

```sql
ORDER BY anomaly_events.scored_at DESC, anomaly_events.id DESC
```

Default list filter:

```sql
WHERE anomaly_events.event_status = 'open'
```

Use pagination from the start. Offset pagination is acceptable for the first
dashboard; cursor pagination can follow once table size grows.

## Security And Secrets

- Do not commit `.env` files or real Kubernetes Secrets.
- Frontend should receive only a public API base URL.
- API should read database credentials from Kubernetes Secrets, not ConfigMaps.
- Never expose `DATABASE_URL`, DB username/password, MQTT credentials, or raw
  Kubernetes Secret values through `/api/system/status`.
- If authentication is required for class/demo use, add it before exposing the
  dashboard outside the private network.

## Open Questions

- Should the API be its own service or be bundled with the frontend container
  in the future consolidated deployment?
- Is the dashboard private-network only, or does it need authentication before
  first deploy?
- Should scoring run history be persisted in a table instead of inferred from
  CSV files and latest `anomaly_events.scored_at`?
- Should model artifacts be indexed into PostgreSQL so the UI does not need to
  reason about PVC paths?
- What severity rules should be automatic, if any, versus operator-assigned?

## First Implementation Batch Recommendation

Start with Phase 1 and a thin slice of Phase 3:

1. Add FastAPI service with read-only anomaly/device/promoted-model endpoints.
2. Add frontend scaffold with the Operations Overview route.
3. Render recent open anomalies and promoted model details.
4. Leave mutation controls disabled until `PATCH /api/anomaly-events/{id}` is
   implemented and tested.

This creates a real dashboard quickly while keeping triage writes behind a
tested API boundary.
