# Plan: Data Pipeline — Cleaning & Feature Engineering

Three-phase pipeline: clean raw data, engineer core features, then add advanced features.

**Date:** 2026-04-25

---

## Phase 1: Data Cleaning

Create `cleaning.py` with focused methods. Runs before any feature engineering.

### Rules

| Issue | Action | Implementation |
|---|---|---|
| Negative watts | Remove rows | `df = df[df["power_watts"] >= 0]` |
| Extreme impossible spikes | Cap at device-safe limit | Per-device: cap at `mean + 4*std` or a global max (e.g. 5000W) |
| Duplicate timestamps | Deduplicate | `df.drop_duplicates(subset=["device_label", "datetime"])` |
| Missing data gaps | Mark with gap feature | Per-device: flag rows where time since previous reading exceeds threshold |
| Near-zero noise | Snap to 0 | Values below threshold (e.g. < 0.5W) set to 0 |

### File: `cleaning.py`
- `clean_data(df) -> df` — orchestrator, calls all below in order
- `_remove_negative_watts(df) -> df`
- `_cap_extreme_spikes(df) -> df` — per device, cap at `mean + 4*std`
- `_deduplicate_timestamps(df) -> df`
- `_mark_data_gaps(df) -> df` — adds `has_gap` boolean column (gap > 5 min)
- `_snap_near_zero(df, threshold=0.5) -> df`

### Update `main.py`
- Import `clean_data` from `cleaning`
- Call `df = clean_data(df)` after fetching, before detection

### Update `detection.py`
- Add `has_gap` to default `feature_cols`

---

## Phase 2: Core Features

Create `features.py`. Runs after cleaning, before model training.

### Features

| Feature | Method |
|---|---|
| `hour_sin` | `_add_time_features()` |
| `hour_cos` | `_add_time_features()` |
| `is_weekend` | `_add_time_features()` |
| `rolling_mean_30m` | `_add_rolling_features()` |
| `rolling_std_30m` | `_add_rolling_features()` |
| `zscore_30m` | `_add_rolling_features()` |
| `delta_from_previous` | `_add_delta_features()` |
| `percent_change` | `_add_delta_features()` |

### File: `features.py`
- `engineer_features(df) -> df` — orchestrator
- `_add_time_features(df) -> df` — `hour_sin`, `hour_cos`, `is_weekend`
- `_add_rolling_features(df) -> df` — `rolling_mean_30m`, `rolling_std_30m`, `zscore_30m` (per device, time-based `rolling('30min')`)
- `_add_delta_features(df) -> df` — `delta_from_previous`, `percent_change` (per device)

### Update `detection.py`
- Remove `get_hour()` — replaced by `features.engineer_features()`
- Update default `feature_cols` to all features

### Edge Cases
- First rows per device: NaN for rolling/diff → fill with 0
- `zscore_30m` division by zero when `rolling_std_30m` == 0 → fill with 0

---

## Phase 3: Advanced Features

Extend `features.py` with additional methods.

### Features

| Feature | Method |
|---|---|
| `rolling_mean_5m` | `_add_short_rolling_features()` |
| `time_since_last_nonzero` | `_add_state_features()` |
| `duration_current_state` | `_add_state_features()` |
| `device_percentile_rank` | `_add_rank_features()` |

### Add to `features.py`
- `_add_short_rolling_features(df) -> df` — `rolling_mean_5m`
- `_add_state_features(df) -> df` — `time_since_last_nonzero`, `duration_current_state` (per device, sorted by datetime)
- `_add_rank_features(df) -> df` — `device_percentile_rank`
- Update `engineer_features()` to call new methods

### Update `detection.py`
- Add Phase 3 features to default `feature_cols`

### Edge Cases
- `time_since_last_nonzero` — first row or always-zero device → fill with 0
- `duration_current_state` — first row per device → 0 seconds
- `rolling_mean_5m` — first rows in window → fill with 0

---

## Execution Order in `main.py`
```
fetch → clean_data(df) → run_per_device_isolation(df) → visualize
                              ↳ engineer_features(df) called inside detection
```
