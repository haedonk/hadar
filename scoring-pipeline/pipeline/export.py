"""CSV export helpers for hourly scoring dry runs."""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from config import config
from pipeline.data_access import RECENT_READING_COLUMNS, fetch_recent_temperature_readings_df, resolve_window

logger = logging.getLogger(__name__)

FUTURE_SCORING_COLUMNS = [
    "scored_at",
    "model_run_id",
    "model_config_name",
    "model_device",
    "model_trained_at",
    "feature_columns",
    "prediction",
    "is_anomaly",
    "anomaly_score",
    "anomaly_reason",
]

FUTURE_EVENT_COLUMNS = [
    "anomaly_event_id",
    "event_type",
    "event_status",
    "event_severity",
    "event_written_at",
]

HOURLY_EXPORT_COLUMNS = RECENT_READING_COLUMNS + FUTURE_SCORING_COLUMNS + FUTURE_EVENT_COLUMNS

RecentReadingsFetcher = Callable[..., Awaitable[pd.DataFrame]]


async def export_recent_readings_csv(
    *,
    output_base_dir: Path | str | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    lookback: timedelta | None = None,
    offset: timedelta | None = None,
    feature_context: timedelta | None = None,
    model_artifact_dir: Path | str | None = None,
    model_run_id: str | None = None,
    model_config_name: str | None = None,
    run_timestamp: datetime | None = None,
    fetcher: RecentReadingsFetcher = fetch_recent_temperature_readings_df,
) -> Path:
    """Fetch recent readings and write a dry-run CSV with the full planned schema."""
    resolved_lookback = lookback or timedelta(hours=config.HOURLY_SCORING_LOOKBACK_HOURS)
    resolved_feature_context = feature_context or timedelta(hours=config.FEATURE_CONTEXT_HOURS)
    if resolved_feature_context < resolved_lookback:
        raise ValueError("feature_context must be greater than or equal to lookback")
    resolved_offset = offset if offset is not None else timedelta(hours=config.HOURLY_SCORING_OFFSET_HOURS)
    if resolved_offset < timedelta(0):
        raise ValueError("offset must be greater than or equal to zero")
    resolved_run_timestamp = run_timestamp or datetime.now(UTC)
    offset_window_end = window_end
    if offset_window_end is None:
        offset_window_end = resolved_run_timestamp - resolved_offset
    resolved_start, resolved_end = resolve_window(
        window_start=window_start,
        window_end=offset_window_end,
        lookback=resolved_lookback,
    )
    context_start = resolved_end - resolved_feature_context
    base_dir = Path(output_base_dir or config.HOURLY_SCORING_OUTPUT_DIR)
    run_dir = base_dir / build_run_directory_name(resolved_run_timestamp, resolved_start, resolved_end)
    logger.debug(
        "Preparing hourly CSV export: base_dir=%s run_dir=%s run_timestamp=%s window_start=%s window_end=%s offset=%s",
        base_dir,
        run_dir,
        resolved_run_timestamp.isoformat(),
        resolved_start.isoformat(),
        resolved_end.isoformat(),
        resolved_offset,
    )
    run_dir.mkdir(parents=True, exist_ok=True)

    df = await fetcher(window_start=context_start, window_end=resolved_end, lookback=resolved_feature_context)
    df = pd.DataFrame(df, columns=RECENT_READING_COLUMNS) if df.empty else df
    logger.debug("Fetched DataFrame for hourly CSV export: shape=%s columns=%s", df.shape, list(df.columns))
    if model_artifact_dir is not None:
        from pipeline.scoring import score_temperature_readings

        df = score_temperature_readings(
            df,
            model_artifact_dir=model_artifact_dir,
            model_run_id=model_run_id or config.MODEL_RUN_ID,
            model_config_name=model_config_name or config.MODEL_CONFIG_NAME,
            scored_at=resolved_run_timestamp,
        )
        logger.debug("Scored DataFrame for hourly CSV export: shape=%s columns=%s", df.shape, list(df.columns))

    target_mask = (pd.to_datetime(df["datetime"], utc=True) >= resolved_start) & (
        pd.to_datetime(df["datetime"], utc=True) < resolved_end
    )
    export_df = with_hourly_export_columns(df.loc[target_mask].copy())
    export_df = convert_datetime_columns_to_output_timezone(export_df)
    logger.debug("Hourly CSV export DataFrame shape after schema normalization: %s", export_df.shape)

    output_path = run_dir / "recent_readings.csv"
    export_df.to_csv(output_path, index=False)

    logger.info(
        "Exported %s recent reading(s) for window %s to %s at %s",
        len(export_df),
        format_window_for_log(resolved_start, resolved_end),
        output_path,
        resolved_run_timestamp.isoformat(),
    )
    return output_path


def with_hourly_export_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame with all dry-run and future scoring/event columns."""
    export_df = df.copy()
    missing_columns = [column for column in HOURLY_EXPORT_COLUMNS if column not in export_df.columns]
    if missing_columns:
        logger.debug("Adding missing hourly export column(s): %s", missing_columns)
    for column in HOURLY_EXPORT_COLUMNS:
        if column not in export_df.columns:
            export_df[column] = ""
    return export_df[HOURLY_EXPORT_COLUMNS]


def convert_datetime_columns_to_output_timezone(df: pd.DataFrame) -> pd.DataFrame:
    """Convert timestamp columns to the configured local output timezone."""
    export_df = df.copy()
    output_timezone = ZoneInfo(config.OUTPUT_TIMEZONE)
    for column in ["datetime", "scored_at", "model_trained_at", "event_written_at"]:
        if column not in export_df.columns or export_df.empty:
            continue
        values = pd.to_datetime(export_df[column], errors="coerce", utc=True)
        converted = values.dt.tz_convert(output_timezone)
        export_df[column] = converted.where(values.notna(), export_df[column])
    return export_df


def build_run_directory_name(run_timestamp: datetime, window_start: datetime, window_end: datetime) -> str:
    """Build a stable run directory name that includes run and window timestamps."""
    return (
        f"{format_timestamp_for_path(run_timestamp)}"
        f"_window_{format_timestamp_for_path(window_start)}_to_{format_timestamp_for_path(window_end)}"
    )


def format_timestamp_for_path(value: datetime) -> str:
    """Format timestamps for filesystem paths."""
    return value.astimezone(ZoneInfo(config.OUTPUT_TIMEZONE)).strftime("%Y%m%dT%H%M%S%z")


def format_window_for_log(window_start: datetime, window_end: datetime) -> str:
    """Format a query window for logs."""
    output_timezone = ZoneInfo(config.OUTPUT_TIMEZONE)
    formatted_start = window_start.astimezone(output_timezone).isoformat()
    formatted_end = window_end.astimezone(output_timezone).isoformat()
    return f"{formatted_start} to {formatted_end}"
