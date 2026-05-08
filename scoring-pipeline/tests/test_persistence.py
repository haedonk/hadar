"""Tests for the anomaly_events persistence path."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pandas as pd
import pytest

from pipeline.persistence import upsert_anomaly_events


def _scored_frame_with_anomalies() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": 101,
                "device_id": uuid4(),
                "device_label": "office_1",
                "temperature": 73.4,
                "datetime": datetime(2026, 5, 7, 14, 0, tzinfo=UTC),
                "prediction": -1,
                "is_anomaly": True,
                "anomaly_score": -0.123,
                "anomaly_reason": "isolation_forest_prediction",
                "model_trained_at": "2026-05-06T22:00:00+00:00",
            },
            {
                "id": 102,
                "device_id": uuid4(),
                "device_label": "office_1",
                "temperature": 70.5,
                "datetime": datetime(2026, 5, 7, 14, 5, tzinfo=UTC),
                "prediction": 1,
                "is_anomaly": False,
                "anomaly_score": 0.21,
                "anomaly_reason": "",
                "model_trained_at": "2026-05-06T22:00:00+00:00",
            },
        ]
    )


@pytest.mark.asyncio
async def test_upsert_anomaly_events_emits_on_conflict_do_update_with_correct_index_elements() -> None:
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    scored = _scored_frame_with_anomalies()

    persisted = await upsert_anomaly_events(
        session,
        scored,
        model_run_id="run-x",
        model_config_name="config-y",
        scored_at=datetime(2026, 5, 7, 14, 10, tzinfo=UTC),
    )

    assert persisted == 1  # only the anomaly row is upserted
    assert session.execute.await_count == 1
    stmt = session.execute.await_args.args[0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))

    # INSERT ... ON CONFLICT DO UPDATE keyed on the agreed unique tuple.
    assert "INSERT INTO anomaly_events" in compiled
    assert "ON CONFLICT" in compiled
    assert "temperature_reading_id" in compiled
    assert "model_run_id" in compiled
    assert "model_config_name" in compiled
    assert "DO UPDATE" in compiled

    # event_status / event_severity must NOT be in the update set -- those are
    # operator-managed and an upsert must not stomp them.
    assert "event_status" not in compiled
    assert "event_severity" not in compiled


@pytest.mark.asyncio
async def test_upsert_anomaly_events_returns_zero_when_no_anomalies() -> None:
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    df = pd.DataFrame(
        [
            {
                "id": 1,
                "device_id": uuid4(),
                "device_label": "office_1",
                "is_anomaly": False,
                "prediction": 1,
                "anomaly_score": 0.5,
                "anomaly_reason": "",
                "model_trained_at": "",
            }
        ]
    )

    persisted = await upsert_anomaly_events(
        session,
        df,
        model_run_id="run-x",
        model_config_name="config-y",
        scored_at=datetime(2026, 5, 7, 14, 10, tzinfo=UTC),
    )

    assert persisted == 0
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_upsert_anomaly_events_returns_zero_for_empty_dataframe() -> None:
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    persisted = await upsert_anomaly_events(
        session,
        pd.DataFrame(),
        model_run_id="run-x",
        model_config_name="config-y",
        scored_at=datetime(2026, 5, 7, 14, 10, tzinfo=UTC),
    )
    assert persisted == 0
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_export_skips_persistence_when_kill_switch_off(monkeypatch, tmp_path) -> None:
    """When ENABLE_ANOMALY_EVENT_PERSISTENCE is false the DB path is not invoked."""
    from pipeline import export

    monkeypatch.setattr(export.config, "ENABLE_ANOMALY_EVENT_PERSISTENCE", False)

    persist_spy = AsyncMock()
    monkeypatch.setattr(export, "_persist_anomaly_events", persist_spy)

    async def fake_fetcher(**kwargs):
        return pd.DataFrame()

    await export.export_recent_readings_csv(
        output_base_dir=tmp_path,
        window_end=datetime(2026, 5, 6, 18, 0, tzinfo=UTC),
        run_timestamp=datetime(2026, 5, 6, 18, 1, 2, tzinfo=UTC),
        model_artifact_dir=tmp_path,
        model_run_id="run-x",
        model_config_name="config-y",
        fetcher=fake_fetcher,
    )

    persist_spy.assert_not_called()


@pytest.mark.asyncio
async def test_export_invokes_persistence_when_kill_switch_on(monkeypatch, tmp_path) -> None:
    from pipeline import export

    monkeypatch.setattr(export.config, "ENABLE_ANOMALY_EVENT_PERSISTENCE", True)

    persist_spy = AsyncMock()
    monkeypatch.setattr(export, "_persist_anomaly_events", persist_spy)

    async def fake_fetcher(**kwargs):
        return pd.DataFrame()

    await export.export_recent_readings_csv(
        output_base_dir=tmp_path,
        window_end=datetime(2026, 5, 6, 18, 0, tzinfo=UTC),
        run_timestamp=datetime(2026, 5, 6, 18, 1, 2, tzinfo=UTC),
        model_artifact_dir=tmp_path,
        model_run_id="run-x",
        model_config_name="config-y",
        fetcher=fake_fetcher,
    )

    persist_spy.assert_awaited_once()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upsert_anomaly_events_is_idempotent_against_real_db() -> None:
    """Re-running with the same rows produces no new rows.

    Skipped by default; requires a reachable test DB and the anomaly_events
    table from db/anomaly_events.sql.
    """
    pytest.skip("Integration test requires a reachable test database with anomaly_events present")
