import pandas as pd

from pipeline.sweep_config import SweepConfig, TrainingSweepConfig
from pipeline.sweeps import run_training_sweep, summarize_sweep_configs


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
