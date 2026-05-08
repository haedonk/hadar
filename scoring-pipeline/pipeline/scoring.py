"""Model artifact loading and Isolation Forest scoring."""

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from pipeline.cleaning import clean_for_scoring
from pipeline.features import extract_features

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeviceArtifacts:
    device: str
    model: Any
    scaler: Any
    metadata: dict[str, Any]


def score_temperature_readings(
    df: pd.DataFrame,
    *,
    model_artifact_dir: Path | str,
    model_run_id: str,
    model_config_name: str,
    scored_at: datetime | None = None,
) -> pd.DataFrame:
    """Score cleaned and featured readings with per-device Isolation Forest artifacts."""
    if df.empty:
        return _empty_scored_frame(df)

    scored_at = scored_at or datetime.now(UTC)
    model_dir = Path(model_artifact_dir)
    cleaned = clean_for_scoring(df)

    # Load per-device artifacts up front so we can build the device_stats map
    # used for the (training-aligned) z-score feature, and skip devices that
    # are missing artifacts or stored stats rather than crashing the run.
    device_artifacts: dict[str, DeviceArtifacts] = {}
    skipped_devices: set[str] = set()
    device_stats: dict[str, dict[str, float]] = {}
    for device, _ in cleaned.groupby("device_label", sort=False):
        device_str = str(device)
        try:
            artifacts = load_device_artifacts(model_dir, device_str)
        except FileNotFoundError:
            logger.warning(
                "No model artifacts for device %s in %s; rows will be returned with empty scoring columns",
                device_str,
                model_dir,
            )
            skipped_devices.add(device_str)
            continue

        stats = _extract_device_stats(artifacts)
        if stats is None:
            logger.warning(
                "Skipping device %s: metadata is missing device_stats / feature_stats_version",
                device_str,
            )
            skipped_devices.add(device_str)
            continue

        device_artifacts[device_str] = artifacts
        device_stats[device_str] = stats

    featured = extract_features(cleaned, device_stats=device_stats or None)

    frames: list[pd.DataFrame] = []
    for device, group in featured.groupby("device_label", sort=False):
        device_str = str(device)
        if device_str in skipped_devices:
            frames.append(_empty_scored_frame(group))
            continue
        artifacts = device_artifacts[device_str]
        frames.append(_score_device_group(group, artifacts, model_run_id, model_config_name, scored_at))

    return pd.concat(frames, ignore_index=True) if frames else _empty_scored_frame(df)


def _extract_device_stats(artifacts: "DeviceArtifacts") -> dict[str, float] | None:
    """Pull per-device temperature mean/std from model metadata.

    Returns ``None`` when the metadata predates ``feature_stats_version`` or
    is missing the ``device_stats`` block, so callers can skip the device
    rather than silently mis-score it. ``temperature_std_f == 0`` (or NaN) is
    coerced to 1.0 to keep the z-score finite — defensive belt-and-suspenders
    on top of the training-side guarantee.
    """
    metadata = artifacts.metadata or {}
    if metadata.get("feature_stats_version", 0) < 1:
        return None
    raw_stats = metadata.get("device_stats")
    if not isinstance(raw_stats, dict):
        return None
    if "temperature_mean_f" not in raw_stats or "temperature_std_f" not in raw_stats:
        return None

    mean_value = float(raw_stats["temperature_mean_f"])
    std_value = float(raw_stats["temperature_std_f"])
    if std_value == 0.0 or std_value != std_value:  # NaN check
        logger.warning(
            "Device %s has temperature_std_f=%s; substituting 1.0 to keep z-score finite",
            artifacts.device,
            std_value,
        )
        std_value = 1.0
    return {"temperature_mean_f": mean_value, "temperature_std_f": std_value}


def load_device_artifacts(model_artifact_dir: Path, device: str) -> DeviceArtifacts:
    """Load model, scaler, and metadata artifacts for one device."""
    safe_name = safe_artifact_name(device)
    model_path = model_artifact_dir / f"{safe_name}_model.joblib"
    scaler_path = model_artifact_dir / f"{safe_name}_scaler.joblib"
    metadata_path = model_artifact_dir / f"{safe_name}_metadata.json"

    missing = [path for path in [model_path, scaler_path, metadata_path] if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing scoring artifact(s) for {device}: {missing}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return DeviceArtifacts(
        device=device,
        model=joblib.load(model_path),
        scaler=joblib.load(scaler_path),
        metadata=metadata,
    )


def safe_artifact_name(device: str) -> str:
    """Return the training-compatible artifact name for a device label."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", device).strip("_") or "device"


def _score_device_group(
    group: pd.DataFrame,
    artifacts: DeviceArtifacts,
    model_run_id: str,
    model_config_name: str,
    scored_at: datetime,
) -> pd.DataFrame:
    result = group.copy()
    feature_columns = list(artifacts.metadata["feature_columns"])
    for column in feature_columns:
        if column not in result.columns:
            result[column] = False if column == "has_gap" else 0.0

    features = result[feature_columns].astype(float)
    scaled = artifacts.scaler.transform(features)
    predictions = np.asarray(artifacts.model.predict(scaled))
    scores = np.asarray(artifacts.model.decision_function(scaled))

    result["scored_at"] = scored_at
    result["model_run_id"] = model_run_id
    result["model_config_name"] = model_config_name
    result["model_device"] = artifacts.metadata.get("device", artifacts.device)
    result["model_trained_at"] = artifacts.metadata.get("trained_at", "")
    result["feature_columns"] = "|".join(feature_columns)
    result["prediction"] = predictions
    result["is_anomaly"] = predictions == -1
    result["anomaly_score"] = scores
    result["anomaly_reason"] = np.where(result["is_anomaly"], "isolation_forest_prediction", "")
    return result


def _empty_scored_frame(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column in [
        "scored_at",
        "model_run_id",
        "model_config_name",
        "model_device",
        "model_trained_at",
        "feature_columns",
        "prediction",
        "is_anomaly",
        "anomaly_score",
        "anomaly_reason",
    ]:
        if column not in result.columns:
            result[column] = ""
    return result
