from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config import config
from pipeline.cleaning import clean_data
from pipeline.data_access import fetch_temperature_readings_df
from pipeline.sweep_config import (
    SweepConfig,
    TrainingSweepConfig,
    copy_source_sweep_config,
    load_sweep_config,
    write_normalized_sweep_config,
)
from pipeline.training import train_per_device_models
from utils.logger import get_logger

logger = get_logger(__name__)


async def run_training_sweep_from_file(config_path: Path, output_base_dir: Path | None = None) -> Path:
    """Load a YAML/CSV sweep config, fetch DB readings, and run all training configs."""
    sweep_config = load_sweep_config(config_path)
    df = await fetch_temperature_readings_df()
    logger.info("Fetched %s rows for training sweep", len(df))

    if config.CLEAN_DATA:
        df = clean_data(df)
        logger.info("After cleaning: %s rows", len(df))

    return run_training_sweep(
        df=df,
        sweep_config=sweep_config,
        output_base_dir=output_base_dir,
        source_config_path=config_path,
    )


def run_training_sweep(
    df: pd.DataFrame,
    sweep_config: SweepConfig,
    output_base_dir: Path | None = None,
    source_config_path: Path | None = None,
) -> Path:
    """Run all configs in a normalized sweep config and write comparison outputs."""
    base_dir = output_base_dir or Path(config.DATA_DIR) / "output" / "training-sweeps"
    run_dir = base_dir / _build_run_id(sweep_config.name)
    configs_dir = run_dir / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)

    write_normalized_sweep_config(sweep_config, run_dir / "sweep_config.normalized.json")
    if source_config_path is not None:
        copy_source_sweep_config(source_config_path, run_dir)

    summary_frames = [
        run_training_config(df=df.copy(), output_dir=configs_dir / training_config.name, config=training_config)
        for training_config in sweep_config.configs
    ]

    sweep_summary = pd.concat(summary_frames, ignore_index=True) if summary_frames else pd.DataFrame()
    sweep_summary.to_csv(run_dir / "sweep_summary.csv", index=False)

    config_summary = summarize_sweep_configs(sweep_summary)
    config_summary.to_csv(run_dir / "config_summary.csv", index=False)

    logger.info("Training sweep completed: %s", run_dir)
    return run_dir


def run_training_config(df: pd.DataFrame, output_dir: Path, config: TrainingSweepConfig) -> pd.DataFrame:
    """Run one training config and write its artifacts and CSV outputs."""
    models_dir = output_dir / "models"
    output_dir.mkdir(parents=True, exist_ok=True)

    results, summary = train_per_device_models(
        df=df,
        models_dir=models_dir,
        contamination=config.contamination,
        random_state=config.random_state,
        test_size=config.test_size,
        min_training_rows=config.min_training_rows,
        n_estimators=config.n_estimators,
        feature_cols=config.feature_columns,
    )

    summary = summary.copy()
    summary.insert(0, "config_name", config.name)
    summary.insert(1, "contamination", config.contamination)
    summary.insert(2, "n_estimators", config.n_estimators)

    summary.to_csv(output_dir / "device_summary.csv", index=False)
    results.to_csv(output_dir / "results.csv", index=False)

    return summary


def summarize_sweep_configs(sweep_summary: pd.DataFrame) -> pd.DataFrame:
    """Build one rollup row per training config."""
    if sweep_summary.empty:
        return pd.DataFrame()

    grouped = sweep_summary.groupby(["config_name", "contamination", "n_estimators"], dropna=False)
    return grouped.agg(
        trained_devices=("status", lambda status: int((status == "trained").sum())),
        skipped_devices=("status", lambda status: int((status == "skipped").sum())),
        total_readings=("total_readings", "sum"),
        total_anomalies=("anomalies", "sum"),
        max_device_anomaly_pct=("anomaly_pct", "max"),
    ).reset_index().assign(
        overall_anomaly_pct=lambda frame: (frame["total_anomalies"] / frame["total_readings"] * 100).round(2)
    )


def _build_run_id(sweep_name: str) -> str:
    safe_name = "".join(character if character.isalnum() or character in "-_" else "-" for character in sweep_name)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}_{safe_name.strip('-') or 'training-sweep'}"
