import json

import pandas as pd

from pipeline.features import MODEL_FEATURE_COLUMNS
from pipeline.training import train_per_device_models


def _training_df(device: str = "sensor-1", rows: int = 12) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "device_label": device,
                "datetime": pd.Timestamp("2026-01-01 00:00:00") + pd.Timedelta(minutes=30 * index),
                "temperature": 70.0 + index * 0.2,
            }
            for index in range(rows)
        ]
    )


def test_train_per_device_models_writes_model_scaler_and_metadata(tmp_path) -> None:
    df = _training_df(device="living room sensor", rows=12)

    results, summary = train_per_device_models(df, models_dir=tmp_path, random_state=7)

    assert "anomaly" in results.columns
    assert summary.loc[0, "status"] == "trained"

    model_path = tmp_path / "living_room_sensor_model.joblib"
    scaler_path = tmp_path / "living_room_sensor_scaler.joblib"
    metadata_path = tmp_path / "living_room_sensor_metadata.json"

    assert model_path.exists()
    assert scaler_path.exists()
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["device"] == "living room sensor"
    assert metadata["feature_columns"] == MODEL_FEATURE_COLUMNS
    assert metadata["row_count"] == 12
    assert metadata["contamination"] == 0.05
    assert metadata["n_estimators"] == 100


def test_train_per_device_models_skips_devices_with_too_few_rows(tmp_path) -> None:
    df = _training_df(rows=3)

    results, summary = train_per_device_models(df, models_dir=tmp_path, min_training_rows=10)

    assert results["anomaly"].tolist() == [1, 1, 1]
    assert summary.loc[0, "status"] == "skipped"
    assert summary.loc[0, "total_readings"] == 3
    assert list(tmp_path.iterdir()) == []


def test_train_per_device_models_uses_custom_contamination_in_metadata(tmp_path) -> None:
    df = _training_df(rows=12)

    train_per_device_models(df, models_dir=tmp_path, contamination=0.1, random_state=7)

    metadata = json.loads((tmp_path / "sensor-1_metadata.json").read_text(encoding="utf-8"))
    assert metadata["contamination"] == 0.1


def test_train_per_device_models_uses_custom_n_estimators_in_metadata(tmp_path) -> None:
    df = _training_df(rows=12)

    train_per_device_models(df, models_dir=tmp_path, n_estimators=25, random_state=7)

    metadata = json.loads((tmp_path / "sensor-1_metadata.json").read_text(encoding="utf-8"))
    assert metadata["n_estimators"] == 25


def test_train_per_device_models_validates_requested_feature_columns(tmp_path) -> None:
    df = _training_df(rows=12)

    try:
        train_per_device_models(df, feature_cols=["missing_feature"], models_dir=tmp_path)
    except ValueError as error:
        assert "missing_feature" in str(error)
    else:
        raise AssertionError("Expected missing feature columns to raise ValueError")
