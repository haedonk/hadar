"""Tests for the scoring pipeline feature extractor."""

from datetime import UTC, datetime, timedelta

import pandas as pd

from pipeline.features import extract_features


def _build_temperature_frame() -> pd.DataFrame:
    base = datetime(2026, 5, 7, 0, 0, tzinfo=UTC)
    rows = []
    for i, temp in enumerate([70.0, 71.0, 72.0, 73.0]):
        rows.append(
            {
                "id": i + 1,
                "device_id": "device-1",
                "device_label": "office_1",
                "temperature": temp,
                "datetime": base + timedelta(minutes=15 * i),
            }
        )
    return pd.DataFrame(rows)


def test_extract_features_uses_device_stats_when_provided() -> None:
    df = _build_temperature_frame()
    device_stats = {
        "office_1": {"temperature_mean_f": 50.0, "temperature_std_f": 5.0},
    }

    featured = extract_features(df, device_stats=device_stats)

    expected = [(70.0 - 50.0) / 5.0, (71.0 - 50.0) / 5.0, (72.0 - 50.0) / 5.0, (73.0 - 50.0) / 5.0]
    assert featured["temperature_zscore"].round(6).tolist() == [round(v, 6) for v in expected]


def test_extract_features_does_not_match_legacy_window_when_device_stats_provided() -> None:
    df = _build_temperature_frame()
    device_stats = {
        "office_1": {"temperature_mean_f": 50.0, "temperature_std_f": 5.0},
    }

    using_stats = extract_features(df, device_stats=device_stats)
    legacy = extract_features(df)

    assert not using_stats["temperature_zscore"].equals(legacy["temperature_zscore"])


def test_extract_features_falls_back_to_legacy_when_device_stats_absent() -> None:
    df = _build_temperature_frame()

    featured = extract_features(df)

    # All four temperatures, mean=71.5, std=sample std ~ 1.291
    mean = df["temperature"].mean()
    std = df["temperature"].std()
    expected = ((df["temperature"] - mean) / std).fillna(0.0)
    assert featured["temperature_zscore"].round(6).tolist() == expected.round(6).tolist()


def test_extract_features_handles_zero_std_via_nan_fill() -> None:
    base = datetime(2026, 5, 7, 0, 0, tzinfo=UTC)
    df = pd.DataFrame(
        [
            {
                "id": 1,
                "device_id": "device-1",
                "device_label": "office_1",
                "temperature": 70.0,
                "datetime": base,
            },
            {
                "id": 2,
                "device_id": "device-1",
                "device_label": "office_1",
                "temperature": 70.0,
                "datetime": base + timedelta(minutes=15),
            },
        ]
    )
    device_stats = {"office_1": {"temperature_mean_f": 70.0, "temperature_std_f": 0.0}}

    featured = extract_features(df, device_stats=device_stats)

    assert featured["temperature_zscore"].tolist() == [0.0, 0.0]
