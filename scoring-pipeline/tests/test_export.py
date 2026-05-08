from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from pipeline.export import (
    HOURLY_EXPORT_COLUMNS,
    build_run_directory_name,
    convert_datetime_columns_to_output_timezone,
    export_recent_readings_csv,
    with_hourly_export_columns,
)


def test_with_hourly_export_columns_adds_future_columns_in_order() -> None:
    df = pd.DataFrame(
        [
            {
                "id": 1,
                "device_id": "device-1",
                "device_label": "office_1",
                "temperature": 70.5,
                "datetime": "2026-05-06T17:30:00+00:00",
            }
        ]
    )

    export_df = with_hourly_export_columns(df)

    assert list(export_df.columns) == HOURLY_EXPORT_COLUMNS
    assert export_df.loc[0, "id"] == 1
    assert export_df.loc[0, "device_label"] == "office_1"
    assert export_df.loc[0, "prediction"] == ""
    assert export_df.loc[0, "event_written_at"] == ""


def test_with_hourly_export_columns_handles_empty_dataframe() -> None:
    export_df = with_hourly_export_columns(pd.DataFrame())

    assert export_df.empty
    assert list(export_df.columns) == HOURLY_EXPORT_COLUMNS


def test_build_run_directory_name_includes_run_and_window_timestamps() -> None:
    run_timestamp = datetime(2026, 5, 6, 18, 1, 2, tzinfo=UTC)
    window_start = datetime(2026, 5, 6, 17, 0, 0, tzinfo=UTC)
    window_end = datetime(2026, 5, 6, 18, 0, 0, tzinfo=UTC)

    name = build_run_directory_name(run_timestamp, window_start, window_end)

    assert name == "20260506T140102-0400_window_20260506T130000-0400_to_20260506T140000-0400"


def test_convert_datetime_columns_to_output_timezone_uses_eastern_time() -> None:
    df = pd.DataFrame(
        [
            {
                "datetime": datetime(2026, 5, 7, 3, 38, 17, tzinfo=UTC),
                "scored_at": "",
                "model_trained_at": "",
                "event_written_at": "",
            }
        ]
    )

    converted = convert_datetime_columns_to_output_timezone(df)

    assert str(converted.loc[0, "datetime"]) == "2026-05-06 23:38:17-04:00"


@pytest.mark.asyncio
async def test_export_recent_readings_csv_writes_full_schema(tmp_path) -> None:
    async def fake_fetcher(**kwargs):
        assert kwargs["window_start"] == datetime(2026, 5, 6, 12, 0, tzinfo=UTC)
        assert kwargs["window_end"] == datetime(2026, 5, 6, 18, 0, tzinfo=UTC)
        assert kwargs["lookback"] == timedelta(hours=6)
        return pd.DataFrame(
            [
                {
                    "id": 1,
                    "device_id": "device-1",
                    "device_label": "office_1",
                    "temperature": 70.5,
                    "datetime": datetime(2026, 5, 6, 17, 30, tzinfo=UTC),
                }
            ]
        )

    output_path = await export_recent_readings_csv(
        output_base_dir=tmp_path,
        window_end=datetime(2026, 5, 6, 18, 0, tzinfo=UTC),
        run_timestamp=datetime(2026, 5, 6, 18, 1, 2, tzinfo=UTC),
        fetcher=fake_fetcher,
    )

    assert output_path.name == "recent_readings.csv"
    assert output_path.parent.name == "20260506T140102-0400_window_20260506T130000-0400_to_20260506T140000-0400"
    assert output_path.exists()

    exported = pd.read_csv(output_path)
    assert list(exported.columns) == HOURLY_EXPORT_COLUMNS
    assert exported.loc[0, "id"] == 1
    assert exported.loc[0, "device_label"] == "office_1"


@pytest.mark.asyncio
async def test_export_recent_readings_csv_offsets_default_window_when_end_is_not_explicit(tmp_path) -> None:
    async def fake_fetcher(**kwargs):
        assert kwargs["window_start"] == datetime(2026, 5, 6, 11, 0, tzinfo=UTC)
        assert kwargs["window_end"] == datetime(2026, 5, 6, 17, 0, tzinfo=UTC)
        assert kwargs["lookback"] == timedelta(hours=6)
        return pd.DataFrame()

    output_path = await export_recent_readings_csv(
        output_base_dir=tmp_path,
        run_timestamp=datetime(2026, 5, 6, 18, 0, tzinfo=UTC),
        offset=timedelta(hours=1),
        fetcher=fake_fetcher,
    )

    assert output_path.parent.name == "20260506T140000-0400_window_20260506T120000-0400_to_20260506T130000-0400"


@pytest.mark.asyncio
async def test_export_recent_readings_csv_writes_header_for_empty_results(tmp_path) -> None:
    async def fake_fetcher(**kwargs):
        return pd.DataFrame()

    output_path = await export_recent_readings_csv(
        output_base_dir=tmp_path,
        window_end=datetime(2026, 5, 6, 18, 0, tzinfo=UTC),
        run_timestamp=datetime(2026, 5, 6, 18, 1, 2, tzinfo=UTC),
        fetcher=fake_fetcher,
    )

    exported = pd.read_csv(output_path)
    assert exported.empty
    assert list(exported.columns) == HOURLY_EXPORT_COLUMNS


@pytest.mark.asyncio
async def test_export_recent_readings_csv_window_mask_is_half_open_in_utc(tmp_path) -> None:
    """Verify the export-time window mask is [start, end) on both sides in UTC."""
    window_start = datetime(2026, 5, 6, 17, 0, tzinfo=UTC)
    window_end = datetime(2026, 5, 6, 18, 0, tzinfo=UTC)

    async def fake_fetcher(**kwargs):
        return pd.DataFrame(
            [
                # 1s before start: excluded
                {"id": 1, "device_id": "d", "device_label": "office_1", "temperature": 70.0,
                 "datetime": window_start - timedelta(seconds=1)},
                # exactly start: included
                {"id": 2, "device_id": "d", "device_label": "office_1", "temperature": 70.0,
                 "datetime": window_start},
                # mid window: included
                {"id": 3, "device_id": "d", "device_label": "office_1", "temperature": 70.0,
                 "datetime": window_start + timedelta(minutes=30)},
                # 1s before end: included
                {"id": 4, "device_id": "d", "device_label": "office_1", "temperature": 70.0,
                 "datetime": window_end - timedelta(seconds=1)},
                # exactly end: excluded (half-open interval)
                {"id": 5, "device_id": "d", "device_label": "office_1", "temperature": 70.0,
                 "datetime": window_end},
            ]
        )

    output_path = await export_recent_readings_csv(
        output_base_dir=tmp_path,
        window_start=window_start,
        window_end=window_end,
        run_timestamp=datetime(2026, 5, 6, 18, 1, 2, tzinfo=UTC),
        fetcher=fake_fetcher,
    )

    exported = pd.read_csv(output_path)
    assert sorted(exported["id"].tolist()) == [2, 3, 4]
