import pandas as pd

from pipeline.training import train_per_device_models


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
    return train_per_device_models(
        df=df,
        feature_cols=feature_cols,
        label_col=label_col,
        random_state=random_state,
        test_size=test_size,
    )
