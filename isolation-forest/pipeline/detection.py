from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from config import config
from utils.logger import get_logger

logger = get_logger(__name__)

MODELS_DIR = Path(config.DATA_DIR) / "models"


def run_per_device_isolation(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    label_col: str = "device_label",
    random_state: int = 42,
    test_size: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit a separate IsolationForest per device and return the DataFrame with an 'anomaly' column.

    Each device gets its own model so that normal temperature ranges are
    learned independently.  The column values follow scikit-learn
    convention: 1 = normal, -1 = anomaly.

    Returns a tuple of (results DataFrame, per-device summary DataFrame).
    """
    if feature_cols is None:
        feature_cols = ["temperature", "hour_sin", "hour_cos"]

    if config.CLEAN_DATA:
        feature_cols.append("has_gap")

    df = df.copy()
    df = get_hour(df)
    df["anomaly"] = 1  # default to normal

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Head of DataFrame:\n{df.head()}")

    device_stats: list[dict] = []
    for device, group in df.groupby(label_col):
        if len(group) < 10:
            continue

        df = _train_device_model(df, group, device, feature_cols, random_state, test_size)
        device_stats.append(_get_device_stats(df, group, device))

    summary_df = pd.DataFrame(device_stats)
    logger.info(f"Per-device summary:\n{summary_df.to_string(index=False)}")

    return df, summary_df


def _train_device_model(
    df: pd.DataFrame,
    group: pd.DataFrame,
    device: str,
    feature_cols: list[str],
    random_state: int,
    test_size: float,
) -> pd.DataFrame:
    """Train an IsolationForest for a single device and update the anomaly column."""
    X = group[feature_cols].astype(float)

    X_train, X_test = train_test_split(X, random_state=random_state, test_size=test_size)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = IsolationForest(contamination=0.05, random_state=random_state)
    model.fit(X_train_scaled)

    df.loc[X_train.index, "anomaly"] = model.predict(X_train_scaled)
    df.loc[X_test.index, "anomaly"] = model.predict(X_test_scaled)

    _save_device_artifacts(device, model, scaler)

    return df


def _save_device_artifacts(device: str, model: IsolationForest, scaler: StandardScaler) -> None:
    """Save model and scaler to the models directory."""
    safe_name = device.replace(" ", "_")
    joblib.dump(model, MODELS_DIR / f"{safe_name}_model.joblib")
    joblib.dump(scaler, MODELS_DIR / f"{safe_name}_scaler.joblib")


def _get_device_stats(df: pd.DataFrame, group: pd.DataFrame, device: str) -> dict:
    """Compute aggregated stats for a single device."""
    device_preds = df.loc[group.index]
    temp = device_preds["temperature"].astype(float)
    n_total = len(group)
    n_anomalies = int((device_preds["anomaly"] == -1).sum())
    n_normal = n_total - n_anomalies
    anomaly_pct = n_anomalies / n_total * 100 if n_total else 0.0

    return {
        "device": device,
        "total_readings": n_total,
        "normal": n_normal,
        "anomalies": n_anomalies,
        "anomaly_pct": round(anomaly_pct, 2),
        "mean_temp": round(float(temp.mean()), 2),
        "std_temp": round(float(temp.std()), 2),
        "min_temp": round(float(temp.min()), 2),
        "max_temp": round(float(temp.max()), 2),
    }


def get_hour(df: pd.DataFrame, datetime_col: str = "datetime") -> pd.DataFrame:
    """Extract hour of day from datetime column with cyclic sin/cos encoding."""
    df = df.copy()
    hour = pd.to_datetime(df[datetime_col]).dt.hour
    df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    return df
