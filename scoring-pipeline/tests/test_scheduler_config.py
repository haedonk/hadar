from pathlib import Path

import pytest

from scheduler.config import load_scheduler_config


def test_load_scheduler_config_reads_hourly_export_job(tmp_path) -> None:
    config_path = tmp_path / "scheduler.yaml"
    config_path.write_text(
        """
timezone: America/New_York
jobs:
  - name: hourly_recent_readings_csv_export
    type: hourly_recent_readings_csv_export
    enabled: true
    trigger: interval
    hours: 1
    lookback_hours: 1
    offset_hours: 1
    feature_context_hours: 6
    model_artifact_dir: /mnt/hadar-model-data/output/training-sweeps/test/models
    model_run_id: test-run
    model_config_name: full_c003_e100
    output_base_dir: /mnt/hadar-data/output/hourly-scoring-runs
""",
        encoding="utf-8",
    )

    config = load_scheduler_config(config_path)

    assert config.timezone == "America/New_York"
    assert len(config.jobs) == 1
    job = config.jobs[0]
    assert job.name == "hourly_recent_readings_csv_export"
    assert job.job_type == "hourly_recent_readings_csv_export"
    assert job.enabled is True
    assert job.trigger == "interval"
    assert job.hours == 1
    assert job.lookback_hours == 1
    assert job.offset_hours == 1
    assert job.feature_context_hours == 6
    assert job.model_artifact_dir == Path("/mnt/hadar-model-data/output/training-sweeps/test/models")
    assert job.model_run_id == "test-run"
    assert job.model_config_name == "full_c003_e100"
    assert job.output_base_dir == Path("/mnt/hadar-data/output/hourly-scoring-runs")


def test_load_scheduler_config_defaults_lookback_and_output_dir(tmp_path) -> None:
    config_path = tmp_path / "scheduler.yaml"
    config_path.write_text(
        """
timezone: America/New_York
jobs:
  - name: hourly_recent_readings_csv_export
    type: hourly_recent_readings_csv_export
    trigger: interval
    hours: 1
""",
        encoding="utf-8",
    )

    config = load_scheduler_config(config_path)

    assert config.jobs[0].lookback_hours == 1
    assert config.jobs[0].offset_hours == 1
    assert config.jobs[0].feature_context_hours == 6
    assert config.jobs[0].output_base_dir == Path("/mnt/hadar-data/output/hourly-scoring-runs")


def test_load_scheduler_config_rejects_unsupported_job_type(tmp_path) -> None:
    config_path = tmp_path / "scheduler.yaml"
    config_path.write_text(
        """
jobs:
  - name: bad_job
    type: training_sweep
    trigger: interval
    hours: 1
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported scoring scheduled job type"):
        load_scheduler_config(config_path)


def test_load_scheduler_config_requires_interval_duration(tmp_path) -> None:
    config_path = tmp_path / "scheduler.yaml"
    config_path.write_text(
        """
jobs:
  - name: hourly_recent_readings_csv_export
    type: hourly_recent_readings_csv_export
    trigger: interval
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires seconds, minutes, or hours"):
        load_scheduler_config(config_path)
