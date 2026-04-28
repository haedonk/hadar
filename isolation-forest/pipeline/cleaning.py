from pathlib import Path
from typing import Dict

import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)


def clean_data(df: pd.DataFrame, output_dir: Path | None = None) -> pd.DataFrame:
    """Orchestrator: applies all cleaning steps in order.

    If output_dir is provided, saves row count statistics to cleaning_stats.csv.
    """
    logger.info(f"Starting data cleaning with {len(df)} rows")

    stats: list[dict] = []
    stats.append({"step": "initial", "rows": len(df)})

    df = _remove_null_temperature(df)
    logger.debug(f"After removing null temperatures: {len(df)} rows")
    stats.append({"step": "remove_null_temperature", "rows": len(df)})

    df = _cap_extreme_values(df)
    logger.debug(f"After capping extreme values: {len(df)} rows")
    stats.append({"step": "cap_extreme_values", "rows": len(df)})

    df = _deduplicate_timestamps(df, output_dir)
    logger.debug(f"After deduplicating timestamps: {len(df)} rows")
    stats.append({"step": "deduplicate_timestamps", "rows": len(df)})

    df = _mark_data_gaps(df)
    logger.debug(f"After marking data gaps: {len(df)} rows")
    stats.append({"step": "mark_data_gaps", "rows": len(df)})

    logger.info("Data cleaning completed")

    if output_dir:
        stats_df = pd.DataFrame(stats)
        stats_file = output_dir / "cleaning_stats.csv"
        stats_df.to_csv(stats_file, index=False)
        logger.info(f"Cleaning statistics saved to {stats_file}")

    return df


def _remove_null_temperature(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows where the temperature value is NULL."""
    return df.dropna(subset=["temperature"]).copy()


def _cap_extreme_values(df: pd.DataFrame) -> pd.DataFrame:
    """Per-device: cap extreme temperature values at mean ± 4*std."""
    df = df.copy()
    # Convert temperature to float to handle Decimal values from database
    df["temperature"] = df["temperature"].astype(float)

    # Calculate per-device statistics
    device_stats: Dict[str, Dict[str, float]] = {}
    for device in df["device_label"].unique():
        device_data = df[df["device_label"] == device]["temperature"]
        mean_val = device_data.mean()
        std_val = device_data.std()
        device_stats[device] = {
            "mean": mean_val,
            "std": std_val,
            "lower": mean_val - 4 * std_val,
            "upper": mean_val + 4 * std_val,
        }

    # Apply capping per device
    for device, cap_stats in device_stats.items():
        mask = df["device_label"] == device
        df.loc[mask, "temperature"] = df.loc[mask, "temperature"].clip(
            lower=cap_stats["lower"], upper=cap_stats["upper"]
        )

    return df


def _deduplicate_timestamps(df: pd.DataFrame, output_dir: Path | None = None) -> pd.DataFrame:
    """Per-device: remove duplicate timestamps."""
    return df.drop_duplicates(subset=["device_label", "datetime", "temperature"]).copy()


def _mark_data_gaps(df: pd.DataFrame, gap_multiplier: float = 1.5) -> pd.DataFrame:
    """Per-device: flag rows where time since previous reading exceeds typical interval.

    Calculates the median time interval between consecutive readings for each device,
    then flags gaps that exceed gap_multiplier times that typical interval.
    Adds a 'has_gap' boolean column.
    """
    df = df.copy()
    df["has_gap"] = False

    # Sort by device and datetime to ensure proper gap detection
    df = df.sort_values(["device_label", "datetime"]).reset_index(drop=True)

    # Calculate typical interval per device (median of time diffs)
    device_typical_intervals: Dict[str, float] = {}
    for device in df["device_label"].unique():
        device_mask = df["device_label"] == device
        device_data = df[device_mask].sort_values("datetime")

        if len(device_data) < 2:
            device_typical_intervals[device] = 300  # Default 5 minutes
            continue

        time_diffs = device_data["datetime"].diff().dropna()
        typical_interval_seconds = time_diffs.median().total_seconds()
        device_typical_intervals[device] = typical_interval_seconds

    # Flag gaps based on device-specific thresholds
    for device in df["device_label"].unique():
        device_mask = df["device_label"] == device
        device_indices = df[device_mask].index
        threshold_seconds = device_typical_intervals[device] * gap_multiplier

        for i in range(1, len(device_indices)):
            current_idx = device_indices[i]
            prev_idx = device_indices[i - 1]

            time_diff = df.loc[current_idx, "datetime"] - df.loc[prev_idx, "datetime"]
            if time_diff.total_seconds() > threshold_seconds:
                df.loc[current_idx, "has_gap"] = True

    return df
