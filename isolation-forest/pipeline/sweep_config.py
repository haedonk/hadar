import csv
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


@dataclass(frozen=True)
class TrainingSweepConfig:
    """One training configuration within a sweep."""

    name: str
    contamination: float
    random_state: int
    test_size: float
    min_training_rows: int
    n_estimators: int
    feature_columns: list[str] | None = None


@dataclass(frozen=True)
class SweepConfig:
    """Normalized sweep configuration loaded from YAML or CSV."""

    name: str
    configs: list[TrainingSweepConfig]


def load_sweep_config(path: Path) -> SweepConfig:
    """Load and validate a sweep config from YAML or CSV."""
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return _load_yaml_sweep_config(path)
    if suffix == ".csv":
        return _load_csv_sweep_config(path)
    raise ValueError(f"Unsupported sweep config format: {path.suffix}")


def write_normalized_sweep_config(config: SweepConfig, path: Path) -> None:
    """Write the normalized sweep config as JSON for reproducibility."""
    path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")


def copy_source_sweep_config(source_path: Path, output_dir: Path) -> Path:
    """Copy the original YAML/CSV config into a sweep output directory."""
    destination = output_dir / f"source_config{source_path.suffix.lower()}"
    shutil.copy2(source_path, destination)
    return destination


def _load_yaml_sweep_config(path: Path) -> SweepConfig:
    if yaml is not None:
        with path.open(encoding="utf-8") as file:
            payload = yaml.safe_load(file) or {}
    else:
        payload = _load_simple_yaml_sweep_config(path)

    if not isinstance(payload, dict):
        raise ValueError("YAML sweep config must be a mapping")

    defaults = payload.get("defaults", {})
    if defaults is None:
        defaults = {}
    if not isinstance(defaults, dict):
        raise ValueError("YAML sweep config defaults must be a mapping")

    raw_configs = payload.get("configs")
    if not isinstance(raw_configs, list) or not raw_configs:
        raise ValueError("YAML sweep config requires a non-empty configs list")

    configs = [_normalize_training_config(raw_config, defaults) for raw_config in raw_configs]
    return _validate_sweep_config(
        SweepConfig(
            name=str(payload.get("name") or path.stem),
            configs=configs,
        )
    )


def _load_csv_sweep_config(path: Path) -> SweepConfig:
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError("CSV sweep config requires at least one row")

    configs = [_normalize_training_config(row, {}) for row in rows]
    return _validate_sweep_config(SweepConfig(name=path.stem, configs=configs))


def _normalize_training_config(raw_config: dict[str, Any], defaults: dict[str, Any]) -> TrainingSweepConfig:
    if not isinstance(raw_config, dict):
        raise ValueError("Each training config must be a mapping")

    merged = {**defaults, **_strip_blank_values(raw_config)}
    missing = [
        key
        for key in ["name", "contamination", "random_state", "test_size", "min_training_rows", "n_estimators"]
        if key not in merged
    ]
    if missing:
        raise ValueError(f"Training config is missing required fields: {missing}")

    return TrainingSweepConfig(
        name=str(merged["name"]),
        contamination=float(merged["contamination"]),
        random_state=int(merged["random_state"]),
        test_size=float(merged["test_size"]),
        min_training_rows=int(merged["min_training_rows"]),
        n_estimators=int(merged["n_estimators"]),
        feature_columns=_normalize_feature_columns(merged.get("feature_columns")),
    )


def _strip_blank_values(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value not in ("", None)}


def _validate_sweep_config(config: SweepConfig) -> SweepConfig:
    if not config.name.strip():
        raise ValueError("Sweep config name cannot be blank")

    seen_names: set[str] = set()
    for training_config in config.configs:
        if not training_config.name.strip():
            raise ValueError("Training config name cannot be blank")
        if training_config.name in seen_names:
            raise ValueError(f"Duplicate training config name: {training_config.name}")
        seen_names.add(training_config.name)

        if not 0 < training_config.contamination <= 0.5:
            raise ValueError(f"Invalid contamination for {training_config.name}: {training_config.contamination}")
        if not 0 < training_config.test_size < 1:
            raise ValueError(f"Invalid test_size for {training_config.name}: {training_config.test_size}")
        if training_config.min_training_rows < 2:
            raise ValueError(
                f"Invalid min_training_rows for {training_config.name}: {training_config.min_training_rows}"
            )
        if training_config.n_estimators < 1:
            raise ValueError(f"Invalid n_estimators for {training_config.name}: {training_config.n_estimators}")
        if training_config.feature_columns is not None and not training_config.feature_columns:
            raise ValueError(f"feature_columns cannot be empty for {training_config.name}")

    return config


def _normalize_feature_columns(value: Any) -> list[str] | None:
    if value in ("", None):
        return None
    if isinstance(value, list):
        return [str(column) for column in value]
    return [column.strip() for column in str(value).split("|") if column.strip()]


def _load_simple_yaml_sweep_config(path: Path) -> dict[str, Any]:
    """Load the simple YAML subset used by sweep config files.

    PyYAML is preferred when installed. This fallback supports the project
    sweep-config shape: top-level scalars, a `defaults` mapping, and a list of
    scalar mappings under `configs`.
    """
    payload: dict[str, Any] = {}
    section: str | None = None
    current_config: dict[str, Any] | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        stripped = line.strip()
        if not line.startswith(" ") and stripped.endswith(":"):
            section = stripped[:-1]
            payload[section] = [] if section == "configs" else {}
            current_config = None
            continue

        if not line.startswith(" ") and ":" in stripped:
            key, value = _split_yaml_key_value(stripped)
            payload[key] = value
            section = None
            current_config = None
            continue

        if section == "defaults":
            key, value = _split_yaml_key_value(stripped)
            payload.setdefault("defaults", {})[key] = value
            continue

        if section == "configs":
            if stripped.startswith("- ") and ":" not in stripped and current_config:
                list_keys = [key for key, value in current_config.items() if isinstance(value, list)]
                if list_keys:
                    current_config[list_keys[-1]].append(stripped[2:].strip().strip("'\""))
                    continue

            if stripped.startswith("- "):
                current_config = {}
                payload.setdefault("configs", []).append(current_config)
                remainder = stripped[2:]
                if remainder:
                    key, value = _split_yaml_key_value(remainder)
                    current_config[key] = value
                continue

            if current_config is None:
                raise ValueError("YAML configs entries must start with '-'")
            if stripped.endswith(":"):
                key = stripped[:-1]
                current_config[key] = []
                continue
            if stripped.startswith("-") and current_config:
                list_keys = [key for key, value in current_config.items() if isinstance(value, list)]
                if not list_keys:
                    raise ValueError(f"Unsupported YAML list item: {raw_line}")
                current_config[list_keys[-1]].append(stripped[1:].strip().strip("'\""))
                continue
            key, value = _split_yaml_key_value(stripped)
            current_config[key] = value
            continue

        raise ValueError(f"Unsupported YAML line: {raw_line}")

    return payload


def _split_yaml_key_value(line: str) -> tuple[str, str]:
    if ":" not in line:
        raise ValueError(f"Expected YAML key/value line: {line}")
    key, value = line.split(":", 1)
    return key.strip(), value.strip().strip("'\"")
