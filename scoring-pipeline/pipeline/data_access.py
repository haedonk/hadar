"""Data access for recent temperature readings."""

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import Select, select

from db import Device, TemperatureReading, get_db

RECENT_READING_COLUMNS = ["id", "device_id", "device_label", "temperature", "datetime"]

SessionFactory = Callable[[], AsyncIterator[Any]]
logger = logging.getLogger(__name__)


def build_recent_temperature_readings_statement(window_start: datetime, window_end: datetime) -> Select:
    """Build the recent temperature readings query for the scoring pipeline."""
    return (
        select(
            TemperatureReading.id,
            TemperatureReading.device_id,
            Device.device_label,
            TemperatureReading.temperature,
            TemperatureReading.ts.label("datetime"),
        )
        .join(Device, Device.id == TemperatureReading.device_id)
        .where(TemperatureReading.ts >= window_start)
        .where(TemperatureReading.ts < window_end)
        .order_by(Device.device_label, TemperatureReading.ts, TemperatureReading.id)
    )


async def fetch_recent_temperature_readings(
    *,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    lookback: timedelta = timedelta(hours=1),
    session_factory: SessionFactory = get_db,
) -> list[dict[str, Any]]:
    """Fetch recent temperature readings joined with device labels."""
    resolved_start, resolved_end = resolve_window(window_start=window_start, window_end=window_end, lookback=lookback)
    stmt = build_recent_temperature_readings_statement(resolved_start, resolved_end)
    logger.debug(
        "Fetching recent temperature readings: window_start=%s window_end=%s lookback=%s",
        resolved_start.isoformat(),
        resolved_end.isoformat(),
        lookback,
    )
    logger.debug("Recent temperature readings SQL: %s", stmt)

    async with session_factory() as session:
        result = await session.execute(stmt)
        rows = [row._asdict() for row in result]

    logger.debug("Fetched %s recent temperature reading row(s)", len(rows))
    if rows:
        logger.debug("First recent reading row: %s", rows[0])
        logger.debug("Last recent reading row: %s", rows[-1])
    return rows


async def fetch_recent_temperature_readings_df(
    *,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    lookback: timedelta = timedelta(hours=1),
    session_factory: SessionFactory = get_db,
) -> pd.DataFrame:
    """Fetch recent temperature readings as a DataFrame with stable columns."""
    rows = await fetch_recent_temperature_readings(
        window_start=window_start,
        window_end=window_end,
        lookback=lookback,
        session_factory=session_factory,
    )
    df = pd.DataFrame(rows, columns=RECENT_READING_COLUMNS)
    logger.debug("Recent temperature readings DataFrame shape=%s columns=%s", df.shape, list(df.columns))
    return df


def resolve_window(
    *,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    lookback: timedelta = timedelta(hours=1),
) -> tuple[datetime, datetime]:
    """Resolve an explicit or lookback-based query window."""
    if lookback <= timedelta(0):
        raise ValueError("lookback must be greater than zero")

    resolved_end = window_end or datetime.now(UTC)
    resolved_start = window_start or resolved_end - lookback

    if resolved_start >= resolved_end:
        raise ValueError("window_start must be before window_end")

    logger.debug(
        "Resolved recent-reading window: start=%s end=%s lookback=%s",
        resolved_start.isoformat(),
        resolved_end.isoformat(),
        lookback,
    )
    return resolved_start, resolved_end


@asynccontextmanager
async def static_session_factory(session: Any) -> AsyncIterator[Any]:
    """Return a fixed async session for tests."""
    yield session
