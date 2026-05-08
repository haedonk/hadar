import json

import pandas as pd
import pytest

from config import config as global_config
from pipeline.sweep_config import SweepConfig, TrainingSweepConfig
from pipeline.sweeps import PROMOTION_MARKER_SCHEMA_VERSION, run_training_sweep, summarize_sweep_configs


def _sweep_df(rows: int = 12) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "device_label": "sensor-1",
                "datetime": pd.Timestamp("2026-01-01 00:00:00") + pd.Timedelta(minutes=30 * index),
                "temperature": 70.0 + index * 0.2,
            }
            for index in range(rows)
        ]
    )


def test_run_training_sweep_writes_outputs_from_parsed_config(tmp_path) -> None:
    source_config = tmp_path / "source.yaml"
    source_config.write_text("name: test-sweep\nconfigs: []\n", encoding="utf-8")
    sweep_config = SweepConfig(
        name="test-sweep",
        configs=[
            TrainingSweepConfig(
                name="contamination_0_01",
                contamination=0.01,
                random_state=7,
                test_size=0.2,
                min_training_rows=10,
                n_estimators=50,
                feature_columns=["temperature", "temperature_zscore"],
            )
        ],
    )

    run_dir = run_training_sweep(
        df=_sweep_df(),
        sweep_config=sweep_config,
        output_base_dir=tmp_path / "output",
        source_config_path=source_config,
    )

    assert (run_dir / "source_config.yaml").exists()
    assert (run_dir / "sweep_config.normalized.json").exists()
    assert (run_dir / "sweep_summary.csv").exists()
    assert (run_dir / "config_summary.csv").exists()
    assert (run_dir / "configs" / "contamination_0_01" / "device_summary.csv").exists()
    assert (run_dir / "configs" / "contamination_0_01" / "results.csv").exists()
    assert (run_dir / "configs" / "contamination_0_01" / "models" / "sensor-1_model.joblib").exists()


@pytest.fixture
def _isolated_marker_path(tmp_path, monkeypatch):
    """Redirect the promotion marker path so each test writes into its own tmp dir."""
    marker_path = tmp_path / "promotion" / "promoted_model.json"
    monkeypatch.setattr(global_config, "PROMOTION_MARKER_PATH", str(marker_path))
    return marker_path


def _build_sweep_config(name: str, configs: list[TrainingSweepConfig]) -> SweepConfig:
    return SweepConfig(name=name, configs=configs)


def _trainable_config(name: str = "promoted") -> TrainingSweepConfig:
    return TrainingSweepConfig(
        name=name,
        contamination=0.01,
        random_state=7,
        test_size=0.2,
        min_training_rows=10,
        n_estimators=25,
        feature_columns=["temperature", "temperature_zscore"],
    )


def test_run_training_sweep_writes_promotion_marker(tmp_path, monkeypatch, _isolated_marker_path) -> None:
    monkeypatch.setattr(global_config, "PROMOTED_CONFIG_NAME", "promoted")
    sweep_config = _build_sweep_config("test-sweep", [_trainable_config("promoted")])

    run_dir = run_training_sweep(
        df=_sweep_df(),
        sweep_config=sweep_config,
        output_base_dir=tmp_path / "output",
    )

    marker_path = _isolated_marker_path
    assert marker_path.exists()

    payload = json.loads(marker_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == run_dir.name
    assert payload["config_name"] == "promoted"
    assert payload["schema_version"] == PROMOTION_MARKER_SCHEMA_VERSION
    assert isinstance(payload["promoted_at"], str) and payload["promoted_at"]

    # Atomic-write contract: no leftover .tmp file alongside the final marker.
    leftover_tmp = list(marker_path.parent.glob("promoted_model.json.tmp"))
    assert leftover_tmp == []


def test_run_training_sweep_skips_marker_when_promoted_config_missing(
    tmp_path, monkeypatch, _isolated_marker_path
) -> None:
    monkeypatch.setattr(global_config, "PROMOTED_CONFIG_NAME", "not_in_sweep")
    sweep_config = _build_sweep_config("test-sweep", [_trainable_config("promoted")])

    # Pre-existing marker should be left untouched.
    _isolated_marker_path.parent.mkdir(parents=True, exist_ok=True)
    _isolated_marker_path.write_text('{"existing":true}', encoding="utf-8")

    run_training_sweep(
        df=_sweep_df(),
        sweep_config=sweep_config,
        output_base_dir=tmp_path / "output",
    )

    assert _isolated_marker_path.read_text(encoding="utf-8") == '{"existing":true}'


def test_run_training_sweep_skips_marker_when_no_devices_trained(
    tmp_path, monkeypatch, _isolated_marker_path
) -> None:
    monkeypatch.setattr(global_config, "PROMOTED_CONFIG_NAME", "promoted")
    # min_training_rows higher than available rows -> all devices skipped.
    config_skipped = TrainingSweepConfig(
        name="promoted",
        contamination=0.01,
        random_state=7,
        test_size=0.2,
        min_training_rows=999,
        n_estimators=25,
        feature_columns=["temperature", "temperature_zscore"],
    )
    sweep_config = _build_sweep_config("test-sweep", [config_skipped])

    run_training_sweep(
        df=_sweep_df(),
        sweep_config=sweep_config,
        output_base_dir=tmp_path / "output",
    )

    assert not _isolated_marker_path.exists()


def test_summarize_sweep_configs_rolls_up_by_config() -> None:
    sweep_summary = pd.DataFrame(
        [
            {
                "config_name": "contamination_0_01",
                "contamination": 0.01,
                "n_estimators": 100,
                "status": "trained",
                "total_readings": 100,
                "anomalies": 1,
                "anomaly_pct": 1.0,
            },
            {
                "config_name": "contamination_0_01",
                "contamination": 0.01,
                "n_estimators": 100,
                "status": "skipped",
                "total_readings": 3,
                "anomalies": 0,
                "anomaly_pct": 0.0,
            },
        ]
    )

    config_summary = summarize_sweep_configs(sweep_summary)

    assert config_summary.loc[0, "trained_devices"] == 1
    assert config_summary.loc[0, "skipped_devices"] == 1
    assert config_summary.loc[0, "n_estimators"] == 100
    assert config_summary.loc[0, "total_readings"] == 103
    assert config_summary.loc[0, "total_anomalies"] == 1
    assert config_summary.loc[0, "overall_anomaly_pct"] == 0.97
