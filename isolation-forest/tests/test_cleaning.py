import pandas as pd

from pipeline.cleaning import _spread_duplicate_timestamps, clean_data


def test_clean_data_converts_temperature_to_fahrenheit() -> None:
    df = pd.DataFrame(
        [
            {"device_label": "plug-1", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 0.0},
            {"device_label": "plug-1", "datetime": pd.Timestamp("2026-01-01 00:05:00"), "temperature": 10.0},
        ]
    )

    cleaned = clean_data(df)

    assert cleaned["temperature"].tolist() == [32.0, 50.0]


def test_spread_duplicate_timestamps_across_next_interval() -> None:
    df = pd.DataFrame(
        [
            {"id": 1, "device_label": "plug-1", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 60.0},
            {"id": 2, "device_label": "plug-1", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 61.0},
            {"id": 3, "device_label": "plug-1", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 62.0},
            {"id": 4, "device_label": "plug-1", "datetime": pd.Timestamp("2026-01-01 00:30:00"), "temperature": 63.0},
        ]
    )

    cleaned = _spread_duplicate_timestamps(df)

    assert cleaned["datetime"].tolist() == [
        pd.Timestamp("2026-01-01 00:00:00"),
        pd.Timestamp("2026-01-01 00:10:00"),
        pd.Timestamp("2026-01-01 00:20:00"),
        pd.Timestamp("2026-01-01 00:30:00"),
    ]


def test_spread_duplicate_timestamps_is_per_device() -> None:
    df = pd.DataFrame(
        [
            {"id": 1, "device_label": "plug-1", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 60.0},
            {"id": 2, "device_label": "plug-1", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 61.0},
            {"id": 3, "device_label": "plug-1", "datetime": pd.Timestamp("2026-01-01 00:10:00"), "temperature": 62.0},
            {"id": 4, "device_label": "plug-2", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 63.0},
            {"id": 5, "device_label": "plug-2", "datetime": pd.Timestamp("2026-01-01 01:00:00"), "temperature": 64.0},
        ]
    )

    cleaned = _spread_duplicate_timestamps(df)
    plug_1 = cleaned[cleaned["device_label"] == "plug-1"]
    plug_2 = cleaned[cleaned["device_label"] == "plug-2"]

    assert plug_1["datetime"].tolist() == [
        pd.Timestamp("2026-01-01 00:00:00"),
        pd.Timestamp("2026-01-01 00:05:00"),
        pd.Timestamp("2026-01-01 00:10:00"),
    ]
    assert plug_2["datetime"].tolist() == [
        pd.Timestamp("2026-01-01 00:00:00"),
        pd.Timestamp("2026-01-01 01:00:00"),
    ]


def test_clean_data_preserves_exact_duplicate_readings() -> None:
    df = pd.DataFrame(
        [
            {"id": 1, "device_label": "plug-1", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 10.0},
            {"id": 2, "device_label": "plug-1", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 10.0},
            {"id": 3, "device_label": "plug-1", "datetime": pd.Timestamp("2026-01-01 00:10:00"), "temperature": 11.0},
        ]
    )

    cleaned = clean_data(df)

    assert len(cleaned) == 3
    assert cleaned["temperature"].tolist() == [50.0, 50.0, 51.8]
    assert cleaned["datetime"].tolist() == [
        pd.Timestamp("2026-01-01 00:00:00"),
        pd.Timestamp("2026-01-01 00:05:00"),
        pd.Timestamp("2026-01-01 00:10:00"),
    ]


def test_spread_duplicate_timestamps_leaves_final_duplicate_group_unchanged() -> None:
    df = pd.DataFrame(
        [
            {"id": 1, "device_label": "plug-1", "datetime": pd.Timestamp("2026-01-01 00:00:00"), "temperature": 60.0},
            {"id": 2, "device_label": "plug-1", "datetime": pd.Timestamp("2026-01-01 00:10:00"), "temperature": 61.0},
            {"id": 3, "device_label": "plug-1", "datetime": pd.Timestamp("2026-01-01 00:10:00"), "temperature": 62.0},
        ]
    )

    cleaned = _spread_duplicate_timestamps(df)

    assert cleaned["datetime"].tolist() == [
        pd.Timestamp("2026-01-01 00:00:00"),
        pd.Timestamp("2026-01-01 00:10:00"),
        pd.Timestamp("2026-01-01 00:10:00"),
    ]
