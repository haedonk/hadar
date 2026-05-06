from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


@dataclass(frozen=True)
class ScheduledJobConfig:
    """One scheduled HADAR job loaded from YAML."""

    name: str
    job_type: str
    enabled: bool
    trigger: str
    config_path: Path
    day_of_week: str | None = None
    hour: int | str | None = None
    minute: int | str | None = None
    seconds: int | None = None
    minutes: int | None = None
    hours: int | None = None


@dataclass(frozen=True)
class SchedulerConfig:
    """Scheduler configuration loaded from YAML."""

    timezone: str
    jobs: list[ScheduledJobConfig]


def load_scheduler_config(path: Path) -> SchedulerConfig:
    """Load and validate scheduler jobs from YAML."""
    payload = _load_yaml_payload(path)
    if not isinstance(payload, dict):
        raise ValueError("Scheduler config must be a mapping")

    raw_jobs = payload.get("jobs")
    if not isinstance(raw_jobs, list) or not raw_jobs:
        raise ValueError("Scheduler config requires a non-empty jobs list")

    jobs = [_normalize_job(raw_job, path.parent) for raw_job in raw_jobs]
    return SchedulerConfig(timezone=str(payload.get("timezone") or "UTC"), jobs=jobs)


def _load_yaml_payload(path: Path) -> dict[str, Any]:
    if yaml is not None:
        with path.open(encoding="utf-8") as file:
            return yaml.safe_load(file) or {}
    return _load_simple_scheduler_yaml(path)


def _normalize_job(raw_job: dict[str, Any], config_dir: Path) -> ScheduledJobConfig:
    if not isinstance(raw_job, dict):
        raise ValueError("Each scheduled job must be a mapping")

    missing = [key for key in ["name", "type", "trigger", "config_path"] if key not in raw_job]
    if missing:
        raise ValueError(f"Scheduled job is missing required fields: {missing}")

    job = ScheduledJobConfig(
        name=str(raw_job["name"]),
        job_type=str(raw_job["type"]),
        enabled=_to_bool(raw_job.get("enabled", True)),
        trigger=str(raw_job["trigger"]),
        config_path=_resolve_path(config_dir, str(raw_job["config_path"])),
        day_of_week=_optional_str(raw_job.get("day_of_week")),
        hour=_optional_cron_value(raw_job.get("hour")),
        minute=_optional_cron_value(raw_job.get("minute")),
        seconds=_optional_int(raw_job.get("seconds")),
        minutes=_optional_int(raw_job.get("minutes")),
        hours=_optional_int(raw_job.get("hours")),
    )
    return _validate_job(job)


def _validate_job(job: ScheduledJobConfig) -> ScheduledJobConfig:
    if not job.name.strip():
        raise ValueError("Scheduled job name cannot be blank")
    if job.job_type != "training_sweep":
        raise ValueError(f"Unsupported scheduled job type: {job.job_type}")
    if job.trigger not in {"cron", "interval"}:
        raise ValueError(f"Unsupported scheduled trigger: {job.trigger}")
    if job.trigger == "cron" and job.hour is None:
        raise ValueError(f"Cron job {job.name} requires hour")
    if job.trigger == "interval" and not any([job.seconds, job.minutes, job.hours]):
        raise ValueError(f"Interval job {job.name} requires seconds, minutes, or hours")
    return job


def _resolve_path(config_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (config_dir / path).resolve()


def _optional_str(value: Any) -> str | None:
    return None if value in ("", None) else str(value)


def _optional_int(value: Any) -> int | None:
    return None if value in ("", None) else int(value)


def _optional_cron_value(value: Any) -> int | str | None:
    if value in ("", None):
        return None
    if isinstance(value, int):
        return value
    value_as_string = str(value).strip()
    return int(value_as_string) if value_as_string.isdigit() else value_as_string


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "on"}


def _load_simple_scheduler_yaml(path: Path) -> dict[str, Any]:
    """Load the simple YAML subset used by scheduler config files."""
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
