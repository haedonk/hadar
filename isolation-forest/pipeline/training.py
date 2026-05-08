import json
import re
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from config import config
from pipeline.features import MODEL_FEATURE_COLUMNS, extract_features
from utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_MODELS_DIR = Path(config.DATA_DIR) / "models"
FEATURE_STATS_VERSION = 1


def train_per_device_models(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    label_col: str = "device_label",
    models_dir: Path | None = None,
    contamination: float = config.ISOLATION_FOREST_CONTAMINATION,
    random_state: int = 42,
    test_size: float = 0.2,
    min_training_rows: int = 10,
    n_estimators: int = 100,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train one Isolation Forest per device and persist model artifacts."""
    if feature_cols is None:
        feature_cols = MODEL_FEATURE_COLUMNS.copy()

    if config.CLEAN_DATA and "has_gap" in df.columns and "has_gap" not in feature_cols:
        feature_cols.append("has_gap")

    output_dir = models_dir or DEFAULT_MODELS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    device_temperature_stats = _compute_device_temperature_stats(df, label_col=label_col)
    df = extract_features(df, label_col=label_col, device_stats=device_temperature_stats)
    df["anomaly"] = 1

    missing_features = [column for column in feature_cols if column not in df.columns]
    if missing_features:
        raise ValueError(f"Missing model feature columns: {missing_features}")

    device_stats: list[dict] = []
    for device, group in df.groupby(label_col):
        if len(group) < min_training_rows:
            logger.info("Skipping %s: only %s rows available", device, len(group))
            device_stats.append(_get_skipped_device_stats(group, device, min_training_rows))
            continue

        df, stats = _train_device_model(
            df=df,
            group=group,
            device=device,
            feature_cols=feature_cols,
            models_dir=output_dir,
            contamination=contamination,
            random_state=random_state,
            test_size=test_size,
            n_estimators=n_estimators,
            temperature_stats=device_temperature_stats.get(device, {}),
        )
        device_stats.append(stats)

    summary_df = pd.DataFrame(device_stats)
    logger.info(f"Per-device training summary:\n{summary_df.to_string(index=False)}")

    return df, summary_df


def _compute_device_temperature_stats(
    df: pd.DataFrame,
    label_col: str,
    temperature_col: str = "temperature",
) -> dict[str, dict[str, float]]:
    """Return per-device temperature mean/std (Fahrenheit) over all training rows.

    Stats are computed once over the full cleaned, F-converted DataFrame so the
    saved metadata reflects the same distribution the model was trained
    against. ``std`` of zero (constant-temperature device) collapses to ``NaN``
    -> serialized as ``NaN`` in the dict; downstream consumers replace it with
    1.0 so the resulting z-score stays finite (and the trailing
    ``fillna(0.0)`` in feature extraction zeros it out).
    """
    if label_col not in df.columns or temperature_col not in df.columns:
        return {}

    grouped = df.groupby(label_col, sort=False)[temperature_col]
    means = grouped.mean()
    stds = grouped.std()

    stats: dict[str, dict[str, float]] = {}
    for device, mean in means.items():
        std = stds.get(device, np.nan)
        std_value = float(std) if pd.notna(std) and float(std) != 0.0 else float("nan")
        stats[device] = {
            "temperature_mean_f": float(mean) if pd.notna(mean) else 0.0,
            "temperature_std_f": std_value,
        }
    return stats


def _train_device_model(
    df: pd.DataFrame,
    group: pd.DataFrame,
    device: str,
    feature_cols: list[str],
    models_dir: Path,
    contamination: float,
    random_state: int,
    test_size: float,
    n_estimators: int,
    temperature_stats: dict[str, float],
) -> tuple[pd.DataFrame, dict]:
    """Train and save artifacts for a single device."""
    X = group[feature_cols].astype(float)
    X_train, X_test = train_test_split(X, random_state=random_state, test_size=test_size)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = IsolationForest(contamination=contamination, n_estimators=n_estimators, random_state=random_state)
    model.fit(X_train_scaled)

    df.loc[X_train.index, "anomaly"] = model.predict(X_train_scaled)
    df.loc[X_test.index, "anomaly"] = model.predict(X_test_scaled)

    artifact_paths = _save_device_artifacts(
        device=device,
        model=model,
        scaler=scaler,
        models_dir=models_dir,
        feature_cols=feature_cols,
        row_count=len(group),
        contamination=contamination,
        n_estimators=n_estimators,
        temperature_stats=temperature_stats,
    )

    return df, _get_trained_device_stats(df, group, device, artifact_paths)


def _save_device_artifacts(
    device: str,
    model: IsolationForest,
    scaler: StandardScaler,
    models_dir: Path,
    feature_cols: list[str],
    row_count: int,
    contamination: float,
    n_estimators: int,
    temperature_stats: dict[str, float],
) -> dict[str, str]:
    """Save model, scaler, and metadata artifacts for a device."""
    safe_name = _safe_artifact_name(device)
    model_path = models_dir / f"{safe_name}_model.joblib"
    scaler_path = models_dir / f"{safe_name}_scaler.joblib"
    metadata_path = models_dir / f"{safe_name}_metadata.json"

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    metadata = {
        "device": device,
        "feature_columns": feature_cols,
        "row_count": row_count,
        "contamination": contamination,
        "n_estimators": n_estimators,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_path": str(model_path),
        "scaler_path": str(scaler_path),
        "device_stats": _serialize_device_stats(temperature_stats),
        "feature_stats_version": FEATURE_STATS_VERSION,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return {
        "model_path": str(model_path),
        "scaler_path": str(scaler_path),
        "metadata_path": str(metadata_path),
    }


def _serialize_device_stats(stats: dict[str, float]) -> dict[str, float]:
    """Convert stat values to plain floats, replacing NaN/zero std with 1.0.

    The training code treats a zero/NaN std as "constant device" and lets the
    trailing ``fillna(0.0)`` in feature extraction zero the z-score. The stored
    metadata mirrors that same fallback (std = 1.0) so scoring callers can
    apply ``(t - mean) / std`` directly without divide-by-zero risk.
    """
    mean = stats.get("temperature_mean_f", 0.0)
    std = stats.get("temperature_std_f", 1.0)
    mean_value = float(mean) if mean is not None and np.isfinite(mean) else 0.0
    std_value = float(std) if std is not None and np.isfinite(std) and float(std) != 0.0 else 1.0
    return {
        "temperature_mean_f": mean_value,
        "temperature_std_f": std_value,
    }


def _safe_artifact_name(device: str) -> str:
    """Return a filesystem-safe artifact name for a device label."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", device).strip("_") or "device"


def _get_trained_device_stats(
    df: pd.DataFrame,
    group: pd.DataFrame,
    device: str,
    artifact_paths: dict[str, str],
) -> dict:
    """Compute training summary stats for a device."""
    device_preds = df.loc[group.index]
    temp = device_preds["temperature"].astype(float)
    n_total = len(group)
    n_anomalies = int((device_preds["anomaly"] == -1).sum())
    n_normal = n_total - n_anomalies
    anomaly_pct = n_anomalies / n_total * 100 if n_total else 0.0

    return {
        "device": device,
        "status": "trained",
        "total_readings": n_total,
        "normal": n_normal,
        "anomalies": n_anomalies,
        "anomaly_pct": round(anomaly_pct, 2),
        "mean_temp_f": round(float(temp.mean()), 2),
        "std_temp_f": round(float(temp.std()), 2),
        "min_temp_f": round(float(temp.min()), 2),
        "max_temp_f": round(float(temp.max()), 2),
        **artifact_paths,
    }


def _get_skipped_device_stats(group: pd.DataFrame, device: str, min_training_rows: int) -> dict:
    """Return summary stats for a device skipped during training."""
    return {
        "device": device,
        "status": "skipped",
        "total_readings": len(group),
        "normal": len(group),
        "anomalies": 0,
        "anomaly_pct": 0.0,
        "skip_reason": f"fewer than {min_training_rows} rows",
        "model_path": "",
        "scaler_path": "",
        "metadata_path": "",
    }
