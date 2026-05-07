from datetime import UTC, datetime

import pandas as pd

from pipeline.scoring import safe_artifact_name, score_temperature_readings


class FakeScaler:
    def transform(self, values):
        return values


class FakeModel:
    def predict(self, values):
        return [-1 if index == len(values) - 1 else 1 for index in range(len(values))]

    def decision_function(self, values):
        return [0.2 if index == 0 else -0.1 for index in range(len(values))]


def test_safe_artifact_name_matches_training_convention() -> None:
    assert safe_artifact_name("office 1/main") == "office_1_main"


def test_score_temperature_readings_populates_scoring_columns(monkeypatch, tmp_path) -> None:
    def fake_load_device_artifacts(model_artifact_dir, device):
        from pipeline.scoring import DeviceArtifacts

        return DeviceArtifacts(
            device=device,
            model=FakeModel(),
            scaler=FakeScaler(),
            metadata={
                "device": device,
                "feature_columns": ["temperature", "temperature_rolling_1h", "has_gap"],
                "trained_at": "2026-05-06T22:00:33+00:00",
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
