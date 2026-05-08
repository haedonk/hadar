# Plan: Post-Promotion Scoring Deploy - 2026-05-08

## Current State

Claude completed the main scoring and promotion implementation batch.

Confirmed from the handoff:

- `scoring-pipeline/pipeline/promotion.py` was added.
- `scoring-pipeline/pipeline/persistence.py` was added.
- New scoring tests cover promotion, persistence, and feature behavior.
- `MODEL_PROMOTION_MARKER_PATH` is wired.
- `ENABLE_ANOMALY_EVENT_PERSISTENCE=false` is wired as the safe default.
- The scorer reads the promotion marker once per scoring tick, so newly
  promoted models can be picked up without restarting the scoring pod.
- The anomaly event UPSERT update set intentionally excludes
  `event_status` and `event_severity`, so operator edits survive re-runs.
- `PyYAML==6.0.2` was already present.
- `device_id` was already present on the scored DataFrame, so no
  `data_access.py` change was needed.

The active markdown plans and review notes from the previous batch have been
archived under `data/archive/planning/`.

## Constraints

- Use the k3s MCP for cluster changes, per repo policy.
- Deploy scoring persistence with the kill switch off first.
- Do not retire the pinned `MODEL_RUN_ID`, `MODEL_CONFIG_NAME`, or
  `MODEL_ARTIFACT_DIR` fallback keys until the promotion marker has run
  successfully for a few cycles.
- Rebuild both `isolation-forest` and `scoring-pipeline` images before deploy.
- Bundle the image bump with the still-open deployment hardening items:
  `imagePullPolicy: IfNotPresent` and readiness checks where appropriate.

## Phase 1 - Local Validation And Test Hygiene

Goal: make the repo quiet and verify Claude's implementation before touching
the cluster.

Tasks:

- Add the integration pytest marker under `[tool.pytest.ini_options]` in
  repo-root `pyproject.toml`:

  ```toml
  markers = ["integration: requires a reachable test database"]
  ```

- Run focused local tests:
  - scoring promotion tests
  - scoring persistence tests
  - scoring feature tests
  - scoring export/scoring tests touched by the batch
  - isolation-forest sweep/training tests touched by the promotion marker

- Run Ruff against the changed services:
  - `scoring-pipeline`
  - `isolation-forest`
  - `db`

Acceptance criteria:

- No pytest marker warning.
- Focused tests pass locally.
- Ruff reports no new issues in the touched services.

## Phase 2 - k3s Manifest Prep

Goal: make the deploy defaults safe before the new images are rolled out.

Tasks:

- Update `k3s/scoring-pipeline/configmap.yaml` through the k3s MCP workflow to
  include:

  ```yaml
  ENABLE_ANOMALY_EVENT_PERSISTENCE: "false"
  ```

- Keep these fallback keys in the scoring ConfigMap for now:
  - `MODEL_RUN_ID`
  - `MODEL_CONFIG_NAME`
  - `MODEL_ARTIFACT_DIR`

- Add or confirm the promotion marker path in cluster config if the runtime
  default does not match the PVC mount:
  - expected marker from scoring container:
    `/mnt/hadar-model-data/output/promoted_model.json`

- Change image pull policy for both deployable services:
  - `k3s/scoring-pipeline/deployment.yaml`
  - `k3s/isolation-forest/deployment.yaml`
  - use `imagePullPolicy: IfNotPresent`

- Decide and implement the readiness probe shape for `scoring-pipeline`.
  Since it is a scheduler process rather than an HTTP service, prefer a probe
  that validates process health and mounted paths instead of pretending an API
  exists.

Acceptance criteria:

- Scoring ConfigMap defaults persistence off.
- Existing model pinning remains available as fallback.
- Both services can restart from cached images if the registry is unavailable.
- Readiness behavior reflects the actual scheduler process.

## Phase 3 - Image Rebuilds

Goal: publish images that contain the new promotion, z-score, and persistence
code before any cluster rollout.

Tasks:

- Build and tag a new `isolation-forest` image.
- Build and tag a new `scoring-pipeline` image.
- Push both images to the registry used by the k3s manifests.
- Record exact tags or digests in the deploy notes.
- Update manifests if moving away from `latest`.

Acceptance criteria:

- k3s can pull or use cached copies of both rebuilt images.
- The image identifiers in the manifests match what was pushed.

## Phase 4 - Deploy With Persistence Disabled

Goal: verify the new code path without writing anomaly events.

Tasks:

- Apply the scoring ConfigMap and Deployment via k3s MCP.
- Roll out the rebuilt `scoring-pipeline` image.
- Confirm pod readiness and scheduler startup.
- Verify hourly CSV output still lands under:
  `/mnt/nas/hadar/scoring-pipeline/output/hourly-scoring-runs/`

- Check logs for:
  - promotion marker load attempt
  - `Loaded promoted model from marker` once the marker exists
  - fallback-to-env warning if the marker does not exist yet
  - z-score/device stats behavior
  - persistence disabled / kill switch off behavior

Acceptance criteria:

- CSV scoring output still works.
- The pod is stable.
- No writes to `anomaly_events` occur while
  `ENABLE_ANOMALY_EVENT_PERSISTENCE=false`.
- Z-score scoring uses stored model stats when available.

## Phase 5 - Run Training Sweep And Verify Promotion Marker

Goal: produce the marker file that scoring will consume on future ticks.

Tasks:

- Roll out the rebuilt `isolation-forest` image.
- Run or wait for the training sweep that selects a promoted model.
- Verify `promoted_model.json` materializes on the PVC at the path visible to
  scoring:
  `/mnt/nas/hadar/isolation-forest/output/promoted_model.json`

- Confirm marker schema includes:
  - `run_id`
  - `config_name`
  - `promoted_at`
  - `schema_version`

- Wait for the next scoring tick or trigger a controlled scoring run.
- Confirm scoring logs show the marker-loaded model rather than the env-pinned
  fallback.

Acceptance criteria:

- The marker exists on the shared PVC.
- Scoring reads the marker without a pod restart.
- Scoring resolves artifacts for the promoted run/config.

## Phase 6 - Enable Event Persistence Smoke

Goal: test DB persistence only after CSV output and marker promotion are
verified.

Tasks:

- Flip `ENABLE_ANOMALY_EVENT_PERSISTENCE` to `"true"` through the k3s MCP
  workflow.
- Run a controlled scoring window with known or likely anomalies.
- Verify rows appear in `anomaly_events`.
- Re-run the same scoring window.
- Confirm the second run produces zero new rows and only idempotent UPSERT
  behavior.
- Manually update `event_status` or `event_severity` on a test row, re-run,
  and confirm that operator-owned fields are not overwritten.

Acceptance criteria:

- Event persistence works when enabled.
- Re-runs are idempotent.
- Operator status/severity edits survive re-runs.

## Phase 7 - Stabilize And Retire Fallbacks Later

Goal: remove temporary deployment crutches only after the marker path has
proven reliable.

Tasks:

- Let marker-based scoring run for several cycles.
- Review logs for marker read failures, artifact path failures, or skipped
  devices.
- Keep the env-pinned model fallback during this observation window.
- After stable cycles, decide whether to retire:
  - `MODEL_RUN_ID`
  - `MODEL_CONFIG_NAME`
  - `MODEL_ARTIFACT_DIR`

- Capture final deploy notes in `data/plans/` or move this plan to
  `data/archive/planning/` when complete.

Acceptance criteria:

- Marker promotion is the normal scoring path.
- Fallback keys are either intentionally retained or retired with confidence.
- The deploy and smoke results are documented.
