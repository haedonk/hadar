import logging
from datetime import UTC, datetime

import pandas as pd

from pipeline.scoring import DeviceArtifacts, safe_artifact_name, score_temperature_readings


class FakeScaler:
    def transform(self, values):
        return values


class FakeModel:
    def predict(self, values):
        return [-1 if index == len(values) - 1 else 1 for index in range(len(values))]

    def decision_function(self, values):
        return [0.2 if index == 0 else -0.1 for index in range(len(values))]


def _metadata_with_stats(device: str, mean_f: float = 68.9, std_f: float = 1.0) -> dict:
    return {
        "device": device,
        "feature_columns": ["temperature", "temperature_rolling_1h", "has_gap", "temperature_zscore"],
        "trained_at": "2026-05-06T22:00:33+00:00",
        "feature_stats_version": 1,
        "device_stats": {
            "temperature_mean_f": mean_f,
            "temperature_std_f": std_f,
        },
    }


def test_safe_artifact_name_matches_training_convention() -> None:
    assert safe_artifact_name("office 1/main") == "office_1_main"


def test_score_temperature_readings_populates_scoring_columns(monkeypatch, tmp_path) -> None:
    def fake_load_device_artifacts(model_artifact_dir, device):
        return DeviceArtifacts(
            device=device,
            model=FakeModel(),
            scaler=FakeScaler(),
            metadata=_metadata_with_stats(device),
        )

    monkeypatch.setattr("pipeline.scoring.load_device_artifacts", fake_load_device_artifacts)
    df = pd.DataFrame(
        [
            {
                "id": 1,
                "device_id": "device-1",
                "device_label": "office_1",
                "temperature": 20.0,
                "datetime": datetime(2026, 5, 6, 22, 0, tzinfo=UTC),
            },
            {
                "id": 2,
                "device_id": "device-1",
                "device_label": "office_1",
                "temperature": 21.0,
                "datetime": datetime(2026, 5, 6, 22, 30, tzinfo=UTC),
            },
        ]
    )

    scored = score_temperature_readings(
        df,
        model_artifact_dir=tmp_path,
        model_run_id="test-run",
        model_config_name="full_c003_e100",
        scored_at=datetime(2026, 5, 7, 0, 0, tzinfo=UTC),
    )

    assert scored["temperature"].round(1).tolist() == [68.0, 69.8]
    assert scored["model_run_id"].tolist() == ["test-run", "test-run"]
    assert scored["model_config_name"].tolist() == ["full_c003_e100", "full_c003_e100"]
    assert scored["prediction"].tolist() == [1, -1]
    assert scored["is_anomaly"].tolist() == [False, True]
    assert scored["anomaly_reason"].tolist() == ["", "isolation_forest_prediction"]


def test_score_temperature_readings_uses_metadata_zscore(monkeypatch, tmp_path) -> None:
    """Z-score should match (t - mean) / std from metadata, not the local window."""

    def fake_load_device_artifacts(model_artifact_dir, device):
        return DeviceArtifacts(
            device=device,
            model=FakeModel(),
            scaler=FakeScaler(),
            metadata=_metadata_with_stats(device, mean_f=50.0, std_f=5.0),
        )

    monkeypatch.setattr("pipeline.scoring.load_device_artifacts", fake_load_device_artifacts)
    df = pd.DataFrame(
        [
            {
                "id": 1,
                "device_id": "device-1",
                "device_label": "office_1",
                "temperature": 20.0,  # cleaning -> 68F
                "datetime": datetime(2026, 5, 6, 22, 0, tzinfo=UTC),
            },
            {
                "id": 2,
                "device_id": "device-1",
                "device_label": "office_1",
                "temperature": 21.0,  # cleaning -> 69.8F
                "datetime": datetime(2026, 5, 6, 22, 30, tzinfo=UTC),
            },
        ]
    )

    scored = score_temperature_readings(
        df,
        model_artifact_dir=tmp_path,
        model_run_id="test-run",
        model_config_name="full_c003_e100",
        scored_at=datetime(2026, 5, 7, 0, 0, tzinfo=UTC),
    )

    expected = [(68.0 - 50.0) / 5.0, (69.8 - 50.0) / 5.0]
    assert scored["temperature_zscore"].round(4).tolist() == [round(v, 4) for v in expected]


def test_score_temperature_readings_skips_missing_artifacts(monkeypatch, tmp_path, caplog) -> None:
    """A device with no artifacts on disk yields blank scoring columns rather than crashing."""

    def fake_load_device_artifacts(model_artifact_dir, device):
        if device == "office_with_model":
            return DeviceArtifacts(
                device=device,
                model=FakeModel(),
                scaler=FakeScaler(),
                metadata=_metadata_with_stats(device),
            )
        raise FileNotFoundError(f"no artifacts for {device}")

    monkeypatch.setattr("pipeline.scoring.load_device_artifacts", fake_load_device_artifacts)

    df = pd.DataFrame(
        [
            {
                "id": 1,
                "device_id": "device-1",
                "device_label": "office_with_model",
                "temperature": 20.0,
                "datetime": datetime(2026, 5, 6, 22, 0, tzinfo=UTC),
            },
            {
                "id": 2,
                "device_id": "device-2",
                "device_label": "office_no_model",
                "temperature": 21.0,
                "datetime": datetime(2026, 5, 6, 22, 30, tzinfo=UTC),
            },
        ]
    )

    with caplog.at_level(logging.WARNING, logger="pipeline.scoring"):
        scored = score_temperature_readings(
            df,
            model_artifact_dir=tmp_path,
            model_run_id="test-run",
            model_config_name="full_c003_e100",
            scored_at=datetime(2026, 5, 7, 0, 0, tzinfo=UTC),
        )

    assert set(scored["device_label"]) == {"office_with_model", "office_no_model"}
    no_model_rows = scored.loc[scored["device_label"] == "office_no_model"]
    assert len(no_model_rows) == 1
    assert no_model_rows.iloc[0]["model_run_id"] == ""
    assert no_model_rows.iloc[0]["prediction"] == ""
    assert no_model_rows.iloc[0]["anomaly_score"] == ""

    with_model_rows = scored.loc[scored["device_label"] == "office_with_model"]
    assert with_model_rows.iloc[0]["model_run_id"] == "test-run"
    assert any(
        "no artifacts for office_no_model" in record.message.lower() or "no model artifacts" in record.message.lower()
        for record in caplog.records
    )


def test_score_temperature_readings_skips_device_when_metadata_missing_stats(monkeypatch, tmp_path, caplog) -> None:
    def fake_load_device_artifacts(model_artifact_dir, device):
        return DeviceArtifacts(
            device=device,
            model=FakeModel(),
            scaler=FakeScaler(),
            metadata={
                "device": device,
                "feature_columns": ["temperature", "has_gap"],
                "trained_at": "2026-05-06T22:00:33+00:00",
                # No feature_stats_version, no device_stats -- legacy artifact
            },
        )

    monkeypatch.setattr("pipeline.scoring.load_device_artifacts", fake_load_device_artifacts)

    df = pd.DataFrame(
        [
            {
                "id": 1,
                "device_id": "device-1",
                "device_label": "office_1",
                "temperature": 20.0,
                "datetime": datetime(2026, 5, 6, 22, 0, tzinfo=UTC),
            }
        ]
    )

    with caplog.at_level(logging.WARNING, logger="pipeline.scoring"):
        scored = score_temperature_readings(
            df,
            model_artifact_dir=tmp_path,
            model_run_id="test-run",
            model_config_name="full_c003_e100",
            scored_at=datetime(2026, 5, 7, 0, 0, tzinfo=UTC),
        )

    assert scored.iloc[0]["prediction"] == ""
    assert any("device_stats" in record.message for record in caplog.records)
