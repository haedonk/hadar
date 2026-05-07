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
    featured = extract_features(cleaned)

    frames = []
    for device, group in featured.groupby("device_label", sort=False):
        artifacts = load_device_artifacts(model_dir, str(device))
        frames.append(_score_device_group(group, artifacts, model_run_id, model_config_name, scored_at))

    return pd.concat(frames, ignore_index=True) if frames else _empty_scored_frame(df)


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
