import pytest

from scheduler.config import load_scheduler_config


def test_load_scheduler_config_reads_training_sweep_job(tmp_path) -> None:
    config_path = tmp_path / "scheduler.yaml"
    config_path.write_text(
        """
timezone: America/New_York
jobs:
  - name: weekly_contamination_sweep
    type: training_sweep
    enabled: true
    trigger: cron
    day_of_week: sun
    hour: 2
    minute: 0
    config_path: ../training-sweeps/example.yaml
""",
        encoding="utf-8",
    )

    config = load_scheduler_config(config_path)

    assert config.timezone == "America/New_York"
    assert config.jobs[0].name == "weekly_contamination_sweep"
    assert config.jobs[0].enabled is True
    assert config.jobs[0].trigger == "cron"
    assert config.jobs[0].hour == 2
    assert config.jobs[0].minute == 0
    assert config.jobs[0].config_path.name == "example.yaml"


def test_load_scheduler_config_allows_cron_hour_expression(tmp_path) -> None:
    config_path = tmp_path / "scheduler.yaml"
    config_path.write_text(
        """
jobs:
  - name: twice_daily_training_sweep
    type: training_sweep
    enabled: true
    trigger: cron
    hour: "6,18"
    minute: 0
    config_path: sweep.csv
""",
        encoding="utf-8",
    )

    config = load_scheduler_config(config_path)

    assert config.jobs[0].hour == "6,18"


def test_load_scheduler_config_rejects_unsupported_job_type(tmp_path) -> None:
    config_path = tmp_path / "scheduler.yaml"
    config_path.write_text(
        """
jobs:
  - name: bad_job
    type: unsupported
    trigger: interval
    minutes: 5
    config_path: sweep.yaml
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported scheduled job type"):
        load_scheduler_config(config_path)


def test_load_scheduler_config_requires_interval_duration(tmp_path) -> None:
    config_path = tmp_path / "scheduler.yaml"
    config_path.write_text(
        """
jobs:
  - name: interval_job
    type: training_sweep
    trigger: interval
    config_path: sweep.yaml
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires seconds, minutes, or hours"):
        load_scheduler_config(config_path)
