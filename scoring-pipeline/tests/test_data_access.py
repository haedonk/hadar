from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pandas as pd
import pytest

from pipeline.data_access import (
    RECENT_READING_COLUMNS,
    build_recent_temperature_readings_statement,
    fetch_recent_temperature_readings_df,
    resolve_window,
    static_session_factory,
)


class FakeRow:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def _asdict(self) -> dict:
        return self.payload


class FakeSession:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.executed_statement = None

    async def execute(self, statement):
        self.executed_statement = statement
        return [FakeRow(row) for row in self.rows]


def test_resolve_window_defaults_to_one_hour_lookback_from_end() -> None:
    window_end = datetime(2026, 5, 6, 18, 0, tzinfo=UTC)

    window_start, resolved_end = resolve_window(window_end=window_end)

    assert window_start == datetime(2026, 5, 6, 17, 0, tzinfo=UTC)
    assert resolved_end == window_end


def test_resolve_window_rejects_invalid_ranges() -> None:
    window_end = datetime(2026, 5, 6, 18, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="window_start must be before window_end"):
        resolve_window(window_start=window_end, window_end=window_end)

    with pytest.raises(ValueError, match="lookback must be greater than zero"):
        resolve_window(window_end=window_end, lookback=timedelta(0))


def test_build_recent_temperature_readings_statement_uses_window_and_device_join() -> None:
    window_start = datetime(2026, 5, 6, 17, 0, tzinfo=UTC)
    window_end = datetime(2026, 5, 6, 18, 0, tzinfo=UTC)

    statement = build_recent_temperature_readings_statement(window_start, window_end)
    compiled = str(statement.compile(compile_kwargs={"literal_binds": False}))

    assert "temperature_readings.ts >= " in compiled
    assert "temperature_readings.ts < " in compiled
    assert "JOIN devices ON devices.id = temperature_readings.device_id" in compiled
    assert "ORDER BY devices.device_label, temperature_readings.ts, temperature_readings.id" in compiled


@pytest.mark.asyncio
async def test_fetch_recent_temperature_readings_df_returns_stable_columns() -> None:
    device_id = uuid4()
    rows = [
        {
            "id": 123,
            "device_id": device_id,
            "device_label": "office_1",
            "temperature": 70.5,
            "datetime": datetime(2026, 5, 6, 17, 30, tzinfo=UTC),
        }
    ]
    session = FakeSession(rows)

    df = await fetch_recent_temperature_readings_df(
        window_end=datetime(2026, 5, 6, 18, 0, tzinfo=UTC),
        session_factory=lambda: static_session_factory(session),
    )

    assert list(df.columns) == RECENT_READING_COLUMNS
    assert df.to_dict("records") == rows
    assert session.executed_statement is not None


@pytest.mark.asyncio
async def test_fetch_recent_temperature_readings_df_returns_empty_frame_with_headers() -> None:
    session = FakeSession([])

    df = await fetch_recent_temperature_readings_df(
        window_end=datetime(2026, 5, 6, 18, 0, tzinfo=UTC),
        session_factory=lambda: static_session_factory(session),
    )

    assert isinstance(df, pd.DataFrame)
    assert df.empty
    assert list(df.columns) == RECENT_READING_COLUMNS
