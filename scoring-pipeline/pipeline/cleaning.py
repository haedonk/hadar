"""Cleaning helpers for scoring data before feature extraction."""

import pandas as pd


def clean_for_scoring(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the training-compatible cleaning needed before scoring."""
    if df.empty:
        cleaned = df.copy()
        if "has_gap" not in cleaned.columns:
            cleaned["has_gap"] = pd.Series(dtype=bool)
        return cleaned

    df = df.dropna(subset=["temperature"]).copy()
    df["temperature"] = df["temperature"].astype(float) * 9 / 5 + 32
    df = _mark_data_gaps(df)
    return df


def _mark_data_gaps(df: pd.DataFrame, gap_multiplier: float = 1.5) -> pd.DataFrame:
    df = df.copy()
    df["has_gap"] = False
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values(["device_label", "datetime"]).reset_index(drop=True)

    for device, device_data in df.groupby("device_label", sort=False):
        if len(device_data) < 2:
            continue

        time_diffs = device_data["datetime"].diff().dropna()
        typical_interval_seconds = time_diffs.median().total_seconds()
        threshold_seconds = typical_interval_seconds * gap_multiplier
        device_indices = device_data.index

        for position in range(1, len(device_indices)):
            current_idx = device_indices[position]
            previous_idx = device_indices[position - 1]
            time_diff = df.loc[current_idx, "datetime"] - df.loc[previous_idx, "datetime"]
            if time_diff.total_seconds() > threshold_seconds:
                df.loc[current_idx, "has_gap"] = True

    return df
