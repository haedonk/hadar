import numpy as np
import pandas as pd

MODEL_FEATURE_COLUMNS = [
    "temperature",
    "temperature_rolling_1h",
    "temperature_rolling_6h",
    "temperature_rate_per_hour",
    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    "temperature_zscore",
]


def extract_features(
    df: pd.DataFrame,
    label_col: str = "device_label",
    datetime_col: str = "datetime",
    temperature_col: str = "temperature",
    device_stats: dict[str, dict[str, float]] | None = None,
) -> pd.DataFrame:
    """Build model-ready temperature features per device.

    When ``device_stats`` is provided, the per-device temperature z-score is
    computed against the supplied ``temperature_mean_f`` / ``temperature_std_f``
    constants instead of recomputing them from the input DataFrame. This lets
    scoring callers reuse the training-time distribution rather than the
    short-window mean/std they happen to have in scope.
    """
    df = df.copy()
    df[datetime_col] = pd.to_datetime(df[datetime_col])
    df[temperature_col] = df[temperature_col].astype(float)

    sort_cols = [label_col, datetime_col]
    if "id" in df.columns:
        sort_cols.append("id")
    df = df.sort_values(sort_cols).reset_index(drop=True)

    df = _add_rolling_temperature_features(df, label_col, datetime_col, temperature_col)
    df = _add_rate_of_change_feature(df, label_col, datetime_col, temperature_col)
    df = _add_time_features(df, datetime_col)
    df = _add_temperature_zscore(df, label_col, temperature_col, device_stats=device_stats)

    return df.replace([np.inf, -np.inf], 0.0).fillna(0.0)


def _add_rolling_temperature_features(
    df: pd.DataFrame,
    label_col: str,
    datetime_col: str,
    temperature_col: str,
) -> pd.DataFrame:
    """Add 1-hour and 6-hour rolling averages scoped to each device."""
    frames = []
    for _, group in df.groupby(label_col, sort=False):
        group = group.sort_values(datetime_col).copy()
        indexed = group.set_index(datetime_col)
        group["temperature_rolling_1h"] = indexed[temperature_col].rolling("1h", min_periods=1).mean().to_numpy()
        group["temperature_rolling_6h"] = indexed[temperature_col].rolling("6h", min_periods=1).mean().to_numpy()
        frames.append(group)

    return pd.concat(frames, ignore_index=True)


def _add_rate_of_change_feature(
    df: pd.DataFrame,
    label_col: str,
    datetime_col: str,
    temperature_col: str,
) -> pd.DataFrame:
    """Add temperature rate of change in degrees per hour, scoped to each device."""
    df = df.copy()
    temperature_delta = df.groupby(label_col, sort=False)[temperature_col].diff()
    hours_delta = df.groupby(label_col, sort=False)[datetime_col].diff().dt.total_seconds() / 3600
    df["temperature_rate_per_hour"] = (temperature_delta / hours_delta).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    return df


def _add_time_features(df: pd.DataFrame, datetime_col: str) -> pd.DataFrame:
    """Add cyclic hour-of-day and day-of-week encodings."""
    df = df.copy()
    datetime = pd.to_datetime(df[datetime_col])

    hour = datetime.dt.hour + datetime.dt.minute / 60 + datetime.dt.second / 3600
    df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24)

    day_of_week = datetime.dt.dayofweek
    df["day_of_week_sin"] = np.sin(2 * np.pi * day_of_week / 7)
    df["day_of_week_cos"] = np.cos(2 * np.pi * day_of_week / 7)

    return df


def _add_temperature_zscore(
    df: pd.DataFrame,
    label_col: str,
    temperature_col: str,
    device_stats: dict[str, dict[str, float]] | None = None,
) -> pd.DataFrame:
    """Add per-device temperature z-score normalization.

    If ``device_stats`` is provided, each row uses the supplied per-device
    ``temperature_mean_f`` / ``temperature_std_f`` constants. Otherwise the
    legacy in-frame ``groupby(label_col).transform("mean"|"std")`` behaviour is
    preserved so existing callers stay correct.

    A ``std`` of zero (or missing) is treated as ``NaN`` so the resulting
    z-score collapses to zero via the trailing ``fillna(0.0)`` — matching the
    legacy behaviour for constant-temperature devices.
    """
    df = df.copy()

    if device_stats is None:
        grouped = df.groupby(label_col, sort=False)[temperature_col]
        mean = grouped.transform("mean")
        std = grouped.transform("std").replace(0, np.nan)
        df["temperature_zscore"] = ((df[temperature_col] - mean) / std).fillna(0.0)
        return df

    mean_map = {device: float(stats.get("temperature_mean_f", 0.0)) for device, stats in device_stats.items()}
    std_map = {
        device: float(stats.get("temperature_std_f", 0.0)) or np.nan for device, stats in device_stats.items()
    }
    mean = df[label_col].map(mean_map)
    std = df[label_col].map(std_map).replace(0, np.nan)
    df["temperature_zscore"] = ((df[temperature_col] - mean) / std).fillna(0.0)
    return df
