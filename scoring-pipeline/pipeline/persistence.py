"""Anomaly event persistence for the scoring pipeline.

Implements the idempotent UPSERT path against ``anomaly_events``. The CSV
remains the authoritative dry-run audit trail; this module is gated by the
``ENABLE_ANOMALY_EVENT_PERSISTENCE`` kill switch so flipping the flag off
returns the service to today's CSV-only behaviour with no other code path.
"""

import logging
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.anomaly_event import AnomalyEvent

logger = logging.getLogger(__name__)

# Columns updated when a row already exists for
# (temperature_reading_id, model_run_id, model_config_name).
# event_status / event_severity are operator-managed and intentionally
# excluded so re-scoring does not stomp triage state.
_UPSERT_UPDATE_COLUMNS = (
    "scored_at",
    "prediction",
    "anomaly_score",
    "anomaly_reason",
    "model_trained_at",
)


async def upsert_anomaly_events(
    session: AsyncSession,
    scored_df: pd.DataFrame,
    *,
    model_run_id: str,
    model_config_name: str,
    scored_at: datetime,
) -> int:
    """Upsert anomaly rows from a scored DataFrame into ``anomaly_events``.

    Filters to ``is_anomaly == True`` rows, builds row dicts mapped to
    ``AnomalyEvent`` columns, and runs a single
    ``INSERT ... ON CONFLICT DO UPDATE`` keyed on
    ``(temperature_reading_id, model_run_id, model_config_name)``.

    Returns the number of rows submitted to the UPSERT (not necessarily the
    number actually changed in the DB).
    """
    if scored_df is None or scored_df.empty:
        return 0
    if "is_anomaly" not in scored_df.columns:
        return 0

    anomalies = scored_df.loc[scored_df["is_anomaly"] == True].copy()  # noqa: E712
    if anomalies.empty:
        return 0

    rows = _build_upsert_rows(
        anomalies,
        model_run_id=model_run_id,
        model_config_name=model_config_name,
        scored_at=scored_at,
    )
    if not rows:
        return 0

    stmt = pg_insert(AnomalyEvent).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["temperature_reading_id", "model_run_id", "model_config_name"],
        set_={column: getattr(stmt.excluded, column) for column in _UPSERT_UPDATE_COLUMNS},
    )
    await session.execute(stmt)
    await session.commit()
    logger.info(
        "Upserted %s anomaly_events row(s) for run_id=%s config_name=%s",
        len(rows),
        model_run_id,
        model_config_name,
    )
    return len(rows)


def _build_upsert_rows(
    anomalies: pd.DataFrame,
    *,
    model_run_id: str,
    model_config_name: str,
    scored_at: datetime,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in anomalies.to_dict(orient="records"):
        reading_id = record.get("id")
        device_id = record.get("device_id")
        prediction = record.get("prediction")
        anomaly_score = record.get("anomaly_score")
        if reading_id is None or device_id is None or prediction is None or anomaly_score is None:
            logger.warning(
                "Skipping anomaly row with missing identity/score fields: id=%s device_id=%s prediction=%s score=%s",
                reading_id,
                device_id,
                prediction,
                anomaly_score,
            )
            continue
        rows.append(
            {
                "temperature_reading_id": int(reading_id),
                "device_id": device_id,
                "model_run_id": model_run_id,
                "model_config_name": model_config_name,
                "model_trained_at": _coerce_optional_datetime(record.get("model_trained_at")),
                "scored_at": scored_at,
                "prediction": int(prediction),
                "anomaly_score": float(anomaly_score),
                "anomaly_reason": _coerce_optional_text(record.get("anomaly_reason")),
            }
        )
    return rows


def _coerce_optional_datetime(value: Any) -> datetime | None:
    if value in (None, "", pd.NaT):
        return None
    if isinstance(value, datetime):
        return value
    try:
        parsed = pd.to_datetime(value, utc=True)
    except (TypeError, ValueError):
        return None
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _coerce_optional_text(value: Any) -> str | None:
    if value in (None, "", pd.NaT):
        return None
    if isinstance(value, float) and value != value:  # NaN
        return None
    return str(value)
