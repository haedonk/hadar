# k3s Single Workload Multi-Container Migration Plan

## Current State

Hadar currently deploys the runtime services as separate Kubernetes workloads:

- `ingestion-pipeline`: long-running MQTT-to-PostgreSQL worker.
- `isolation-forest`: long-running APScheduler training/sweep worker.
- `scoring-pipeline`: long-running APScheduler hourly scoring worker.
- `isolation-forest` CronJob: legacy suspended scheduled job.

Each active service has its own Deployment, ConfigMap reference, secret reference, resource budget, container image, and PVC subPath. This gives independent rollout and restart behavior, but it also means shared data contracts, image updates, and environment changes have to be coordinated across several manifests.

## Target Shape

Move the active Hadar runtime into one Deployment whose pod template contains multiple containers:

- `ingestion-pipeline` container.
- `isolation-forest` scheduler container.
- `scoring-pipeline` scheduler container.

The containers would still use separate images and commands. The Deployment would own one replica of a combined pod, and the pod would mount the same retained `hadar-data-pvc` with service-specific subPaths plus the read-only model-data mount needed by scoring.

The Service object should only expose actual network ports. Today these workloads are workers and schedulers, not HTTP servers. A single Service is only useful after one of these exists:

- a real HTTP API/dashboard container,
- a health/metrics sidecar,
- or explicit health endpoints inside each service.

Until then, a Service can be omitted or created later as part of adding health/metrics exposure.

## Immediate Manifest Changes Already Made

These deployment-safe changes are ready now:

- Set `ENABLE_ANOMALY_EVENT_PERSISTENCE: "false"` in `k3s/scoring-pipeline/configmap.yaml` so DB anomaly-event writes stay disabled on first deploy.
- Set `MODEL_PROMOTION_MARKER_PATH: /mnt/hadar-model-data/output/promoted_model.json` in `k3s/scoring-pipeline/configmap.yaml` so the marker location is explicit and matches the mounted isolation-forest data path.
- Change `imagePullPolicy` from `Always` to `IfNotPresent` for `scoring-pipeline`.
- Change `imagePullPolicy` from `Always` to `IfNotPresent` for `isolation-forest` Deployment and the suspended legacy CronJob.

No readiness probe was added. Both active isolation-forest and scoring-pipeline services are APScheduler processes without an HTTP health endpoint or command that proves the scheduler is alive and loaded correctly. A correct readiness design should be added before wiring probes into manifests.

## Manifest Changes Needed For The Combined Workload

Create a new manifest, likely `k3s/hadar-app/deployment.yaml`, with:

- `kind: Deployment`, `metadata.name: hadar-app`.
- One pod template with labels such as `app: hadar-app`.
- Three containers using the existing image names and commands.
- Per-container `envFrom` entries pointing to the existing ConfigMaps and Secrets.
- Per-container `resources` copied from the existing deployments, then tuned after observation.
- Shared `hadar-data` PVC volume.
- Service-specific subPath mounts:
  - ingestion: `/mnt/hadar-data`, `subPath: ingestion-pipeline`.
  - isolation forest: `/mnt/hadar-data`, `subPath: isolation-forest`.
  - scoring: `/mnt/hadar-data`, `subPath: scoring-pipeline`.
  - scoring model read mount: `/mnt/hadar-model-data`, `subPath: isolation-forest`, `readOnly: true`.

ConfigMaps can remain separate at first. Merging them would make the pod manifest shorter but raises the risk of accidental key collisions and makes ownership less clear. Keep the current per-service ConfigMaps for the first migration.

Secrets can also remain separate. Today scoring reuses `isolation-forest-creds` for DB credentials. That is acceptable for the first pass, but a later cleanup should either create a shared DB secret name or service-specific secrets with least-privilege database users.

## Service Exposure

Do not create a Service that exposes fake ports. The active containers do not listen for inbound traffic.

If the project adds a health or API surface, create `k3s/hadar-app/service.yaml` with named ports, for example:

- `api` for a future API/dashboard container.
- `metrics` for a metrics/health sidecar.

If only health checks are needed, prefer a small explicit health endpoint in each service or a lightweight sidecar that reports process and scheduler status. Avoid a Service until there is something real to route to.

## Readiness And Liveness Design

Current blocker: the scheduler containers do not expose a health endpoint.

Recommended design:

- Add per-service health state files under each writable data dir, updated after config load and scheduler start.
- Add a lightweight command probe that verifies the health file freshness and, where possible, process state.
- Or add an HTTP health endpoint / metrics sidecar if the project wants Prometheus-style visibility.

Readiness should only pass after:

- configuration loaded successfully,
- database connectivity succeeds where required,
- scheduler has registered enabled jobs,
- required mounts are visible,
- scoring can resolve either the promotion marker or env fallback model artifacts.

Liveness should be more conservative than readiness. It should not kill a container during a long but valid training sweep or scoring run.

## Tradeoffs

Benefits:

- One rollout can coordinate compatible ingestion/training/scoring image and config changes.
- Shared PVC layout and model promotion marker behavior become easier to reason about inside one pod.
- Fewer top-level workloads to apply and inspect.
- A future health/metrics sidecar can observe all local containers through the same pod context.

Costs:

- Rollout blast radius increases. Updating one container recreates the whole pod and restarts all three services.
- Failure coupling increases. A CrashLoop in one required container prevents the combined pod from becoming healthy.
- Resource scheduling becomes all-or-nothing; the node must have capacity for every container together.
- Logs and restarts are still per-container, but operational triage starts from one larger pod.
- Independent scaling is lost. This is acceptable now because each service runs as a singleton worker, but it would be a blocker if ingestion or scoring needs separate horizontal scaling later.

## Migration Phases

### Phase 1: Harden Current Separate Deployments

- Deploy the current manifest updates with anomaly persistence disabled.
- Rebuild and publish or preload fresh `isolation-forest` and `scoring-pipeline` images.
- Verify scoring still writes CSVs.
- Verify logs show marker loading or env fallback.
- Run a training sweep and verify `/mnt/hadar-data/output/promoted_model.json` materializes from the isolation-forest container.
- Flip `ENABLE_ANOMALY_EVENT_PERSISTENCE` only after the CSV and marker paths are proven.

### Phase 2: Add Health Design

- Add service-level health checks in code or a sidecar design.
- Add readiness/liveness probes to the separate deployments first.
- Confirm probes do not restart long-running valid jobs.
- Document expected `kubectl describe pod` and log behavior for failed DB, missing marker, and malformed config cases.

### Phase 3: Create Combined Deployment In Parallel

- Add `k3s/hadar-app/deployment.yaml`.
- Keep existing per-service manifests in place while the combined deployment is tested.
- Start with `replicas: 0` or do not apply it by default until migration.
- Use the same ConfigMaps, Secrets, PVC, and image tags as the working separate deployments.
- Add a README section explaining that only one deployment style should be active at a time to avoid duplicate ingestion, duplicate scheduler jobs, and duplicate scoring writes.

### Phase 4: Staging Smoke

- Scale separate deployments down or suspend their schedulers in a controlled environment.
- Scale `hadar-app` up to one replica.
- Verify all three containers start.
- Verify ingestion consumes MQTT messages once.
- Verify training sweep writes artifacts and promotion marker once.
- Verify scoring reads the marker, writes CSV output, and, when enabled, anomaly-event upsert remains idempotent.

### Phase 5: Production Cutover

- Apply ConfigMaps and Secrets.
- Scale separate deployments to zero.
- Apply or scale `hadar-app` to one replica.
- Watch all container logs separately:
  - `kubectl -n hadar logs deployment/hadar-app -c ingestion-pipeline`
  - `kubectl -n hadar logs deployment/hadar-app -c isolation-forest`
  - `kubectl -n hadar logs deployment/hadar-app -c scoring-pipeline`
- Confirm there are no duplicate scheduler executions.
- Keep old manifests for one rollback window.

### Phase 6: Cleanup

- Retire old separate Deployment manifests after the combined workload survives the rollback window.
- Decide whether the suspended legacy CronJob should be deleted or retained as an emergency manual path.
- Consolidate docs around the active deployment model.
- Revisit image tags. `IfNotPresent` works best with immutable tags, not `latest`.

## Open Decisions

- Whether to keep per-service ConfigMaps or merge into one `hadar-app-config`.
- Whether to create a dedicated scoring DB secret instead of reusing `isolation-forest-creds`.
- Whether `ingestion-pipeline` belongs in the combined pod or should stay separately restartable because it handles live MQTT consumption.
- Whether the single Service should wait for a real API/health endpoint.
- Whether the project should move away from `latest` tags when using `IfNotPresent`.
