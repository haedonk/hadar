"""Scheduler configuration for hourly scoring exports."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import config

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


@dataclass(frozen=True)
class ScheduledScoringJobConfig:
    """One scheduled scoring job loaded from YAML."""

    name: str
    job_type: str
    enabled: bool
    trigger: str
    output_base_dir: Path
    lookback_hours: float = 1.0
    offset_hours: float = 1.0
    feature_context_hours: float = 6.0
    model_artifact_dir: Path | None = None
    model_run_id: str = ""
    model_config_name: str = ""
    seconds: int | None = None
    minutes: int | None = None
    hours: int | None = None


@dataclass(frozen=True)
class ScoringSchedulerConfig:
    """Scoring scheduler configuration loaded from YAML."""

    timezone: str
    jobs: list[ScheduledScoringJobConfig]


def load_scheduler_config(path: Path) -> ScoringSchedulerConfig:
    """Load and validate scoring scheduler jobs from YAML."""
    payload = _load_yaml_payload(path)
    if not isinstance(payload, dict):
        raise ValueError("Scoring scheduler config must be a mapping")

    raw_jobs = payload.get("jobs")
    if not isinstance(raw_jobs, list) or not raw_jobs:
        raise ValueError("Scoring scheduler config requires a non-empty jobs list")

    jobs = [_normalize_job(raw_job) for raw_job in raw_jobs]
    return ScoringSchedulerConfig(timezone=str(payload.get("timezone") or config.SCHEDULER_TIMEZONE), jobs=jobs)


def _normalize_job(raw_job: dict[str, Any]) -> ScheduledScoringJobConfig:
    if not isinstance(raw_job, dict):
        raise ValueError("Each scoring scheduled job must be a mapping")

    missing = [key for key in ["name", "type", "trigger"] if key not in raw_job]
    if missing:
        raise ValueError(f"Scoring scheduled job is missing required fields: {missing}")

    job = ScheduledScoringJobConfig(
        name=str(raw_job["name"]),
        job_type=str(raw_job["type"]),
        enabled=_to_bool(raw_job.get("enabled", True)),
        trigger=str(raw_job["trigger"]),
        output_base_dir=Path(str(raw_job.get("output_base_dir") or config.HOURLY_SCORING_OUTPUT_DIR)),
        lookback_hours=float(raw_job.get("lookback_hours") or config.HOURLY_SCORING_LOOKBACK_HOURS),
        offset_hours=float(raw_job.get("offset_hours") or config.HOURLY_SCORING_OFFSET_HOURS),
        feature_context_hours=float(raw_job.get("feature_context_hours") or config.FEATURE_CONTEXT_HOURS),
        model_artifact_dir=Path(str(raw_job.get("model_artifact_dir") or config.MODEL_ARTIFACT_DIR)),
        model_run_id=str(raw_job.get("model_run_id") or config.MODEL_RUN_ID),
        model_config_name=str(raw_job.get("model_config_name") or config.MODEL_CONFIG_NAME),
        seconds=_optional_int(raw_job.get("seconds")),
        minutes=_optional_int(raw_job.get("minutes")),
        hours=_optional_int(raw_job.get("hours")),
    )
    return _validate_job(job)


def _validate_job(job: ScheduledScoringJobConfig) -> ScheduledScoringJobConfig:
    if not job.name.strip():
        raise ValueError("Scoring scheduled job name cannot be blank")
    if job.job_type != "hourly_recent_readings_csv_export":
        raise ValueError(f"Unsupported scoring scheduled job type: {job.job_type}")
    if job.trigger != "interval":
        raise ValueError(f"Unsupported scoring scheduled trigger: {job.trigger}")
    if not any([job.seconds, job.minutes, job.hours]):
        raise ValueError(f"Interval job {job.name} requires seconds, minutes, or hours")
    if job.lookback_hours <= 0:
        raise ValueError(f"Interval job {job.name} requires lookback_hours greater than zero")
    if job.offset_hours < 0:
        raise ValueError(f"Interval job {job.name} requires offset_hours greater than or equal to zero")
    if job.feature_context_hours < job.lookback_hours:
        raise ValueError(f"Interval job {job.name} requires feature_context_hours >= lookback_hours")
    return job


def _load_yaml_payload(path: Path) -> dict[str, Any]:
    if yaml is not None:
        with path.open(encoding="utf-8") as file:
            return yaml.safe_load(file) or {}
    return _load_simple_scheduler_yaml(path)


def _optional_int(value: Any) -> int | None:
    return None if value in ("", None) else int(value)


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "on"}


def _load_simple_scheduler_yaml(path: Path) -> dict[str, Any]:
    """Load the simple YAML subset used by scoring scheduler config files."""
    payload: dict[str, Any] = {}
    section: str | None = None
    current_job: dict[str, Any] | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        stripped = line.strip()
        if not line.startswith(" ") and stripped.endswith(":"):
            section = stripped[:-1]
            payload[section] = [] if section == "jobs" else {}
            current_job = None
            continue

        if not line.startswith(" ") and ":" in stripped:
            key, value = _split_yaml_key_value(stripped)
            payload[key] = value
            section = None
            current_job = None
            continue

        if section == "jobs":
            if stripped.startswith("- "):
                current_job = {}
                payload.setdefault("jobs", []).append(current_job)
                remainder = stripped[2:]
                if remainder:
                    key, value = _split_yaml_key_value(remainder)
                    current_job[key] = value
                continue

            if current_job is None:
                raise ValueError("YAML jobs entries must start with '-'")
            key, value = _split_yaml_key_value(stripped)
            current_job[key] = value
            continue

        raise ValueError(f"Unsupported YAML line: {raw_line}")

    return payload


def _split_yaml_key_value(line: str) -> tuple[str, str]:
    if ":" not in line:
        raise ValueError(f"Expected YAML key/value line: {line}")
    key, value = line.split(":", 1)
    return key.strip(), value.strip().strip("'\"")
