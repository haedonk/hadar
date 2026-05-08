import math

import pandas as pd

from pipeline.features import MODEL_FEATURE_COLUMNS, extract_features


def test_extract_features_preserves_rows_and_adds_model_columns() -> None:
    df = pd.DataFrame(
        [
            {"device_label": "sensor-1", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 70.0},
            {"device_label": "sensor-1", "datetime": pd.Timestamp("2026-01-01 01:00:00"), "temperature": 72.0},
        ]
    )

    features = extract_features(df)

    assert len(features) == len(df)
    for column in MODEL_FEATURE_COLUMNS:
        assert column in features.columns


def test_rolling_features_are_scoped_per_device() -> None:
    df = pd.DataFrame(
        [
            {"device_label": "sensor-1", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 70.0},
            {"device_label": "sensor-1", "datetime": pd.Timestamp("2026-01-01 00:30:00"), "temperature": 74.0},
            {"device_label": "sensor-2", "datetime": pd.Timestamp("2026-01-01 00:30:00"), "temperature": 40.0},
        ]
    )

    features = extract_features(df)
    sensor_1 = features[features["device_label"] == "sensor-1"]
    sensor_2 = features[features["device_label"] == "sensor-2"]

    assert sensor_1["temperature_rolling_1h"].tolist() == [70.0, 72.0]
    assert sensor_2["temperature_rolling_1h"].tolist() == [40.0]


def test_rate_of_change_is_degrees_per_hour() -> None:
    df = pd.DataFrame(
        [
            {"device_label": "sensor-1", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 70.0},
            {"device_label": "sensor-1", "datetime": pd.Timestamp("2026-01-01 00:30:00"), "temperature": 74.0},
            {"device_label": "sensor-1", "datetime": pd.Timestamp("2026-01-01 01:30:00"), "temperature": 73.0},
        ]
    )

    features = extract_features(df)

    assert features["temperature_rate_per_hour"].tolist() == [0.0, 8.0, -1.0]


def test_time_features_are_cyclic_and_bounded() -> None:
    df = pd.DataFrame(
        [
            {"device_label": "sensor-1", "datetime": pd.Timestamp("2026-01-05 06:00:00"), "temperature": 70.0},
        ]
    )

    features = extract_features(df)

    assert math.isclose(features.loc[0, "hour_sin"], 1.0)
    assert math.isclose(features.loc[0, "hour_cos"], 0.0, abs_tol=1e-12)
    for column in ["hour_sin", "hour_cos", "day_of_week_sin", "day_of_week_cos"]:
        assert features[column].between(-1, 1).all()


def test_temperature_zscore_is_per_device() -> None:
    df = pd.DataFrame(
        [
            {"device_label": "sensor-1", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 70.0},
            {"device_label": "sensor-1", "datetime": pd.Timestamp("2026-01-01 01:00:00"), "temperature": 72.0},
            {"device_label": "sensor-2", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 100.0},
            {"device_label": "sensor-2", "datetime": pd.Timestamp("2026-01-01 01:00:00"), "temperature": 100.0},
        ]
    )

    features = extract_features(df)
    sensor_1 = features[features["device_label"] == "sensor-1"]
    sensor_2 = features[features["device_label"] == "sensor-2"]

    assert sensor_1["temperature_zscore"].round(6).tolist() == [-0.707107, 0.707107]
    assert sensor_2["temperature_zscore"].tolist() == [0.0, 0.0]


def test_extract_features_does_not_emit_nan_or_infinite_values_for_single_row_device() -> None:
    df = pd.DataFrame(
        [
            {"device_label": "sensor-1", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 70.0},
        ]
    )

    features = extract_features(df)

    assert features[MODEL_FEATURE_COLUMNS].notna().all().all()
    assert features["temperature_rate_per_hour"].tolist() == [0.0]


def test_extract_features_uses_supplied_device_stats_for_zscore() -> None:
    df = pd.DataFrame(
        [
            {"device_label": "sensor-1", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 72.0},
            {"device_label": "sensor-1", "datetime": pd.Timestamp("2026-01-01 01:00:00"), "temperature": 78.0},
        ]
    )
    device_stats = {"sensor-1": {"temperature_mean_f": 70.0, "temperature_std_f": 2.0}}

    features = extract_features(df, device_stats=device_stats)

    # Z-scores match (t - mean) / std exactly because explicit stats were provided.
    assert features["temperature_zscore"].round(6).tolist() == [1.0, 4.0]


def test_extract_features_constant_temperature_device_with_unit_std_yields_zero_zscore() -> None:
    df = pd.DataFrame(
        [
            {"device_label": "sensor-1", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 70.0},
            {"device_label": "sensor-1", "datetime": pd.Timestamp("2026-01-01 01:00:00"), "temperature": 70.0},
        ]
    )
    # Mirrors the persisted-metadata fallback: std=1.0 for a constant device.
    device_stats = {"sensor-1": {"temperature_mean_f": 70.0, "temperature_std_f": 1.0}}

    features = extract_features(df, device_stats=device_stats)

    assert features["temperature_zscore"].tolist() == [0.0, 0.0]
    assert features["temperature_zscore"].notna().all()
