from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from queries import (
    build_anomaly_events_statement,
    build_device_anomaly_events_statement,
    build_device_status_statement,
    build_energy_readings_statement,
    build_summary_statement,
    build_temperature_readings_statement,
    decimal_to_float,
    format_device_status,
    format_reading,
    severity_from_rank,
)
from schemas import AnomalyEventItem, DeviceAnomalyEventItem, DeviceStatus


def compile_statement(statement) -> str:
    return str(statement.compile(compile_kwargs={"literal_binds": False}))


def test_severity_from_rank_maps_known_ranks() -> None:
    assert severity_from_rank(3) == "high"
    assert severity_from_rank(2) == "medium"
    assert severity_from_rank(1) == "low"
    assert severity_from_rank(0) is None
    assert severity_from_rank(None) is None


def test_format_device_status_uses_rank_and_defaults_count() -> None:
    device_id = uuid4()
    last_seen = datetime(2026, 5, 8, 2, 14, tzinfo=UTC)

    assert format_device_status(
        {
            "id": device_id,
            "label": "Office plug",
            "type": "plug",
            "description": "Office outlet",
            "severity_rank": 3,
            "open_anomaly_count": None,
            "last_seen": last_seen,
        }
    ) == {
        "id": device_id,
        "label": "Office plug",
        "type": "plug",
        "description": "Office outlet",
        "current_severity": "high",
        "open_anomaly_count": 0,
        "last_seen": last_seen,
    }


def test_response_models_accept_nullable_database_fields() -> None:
    device_id = uuid4()
    scored_at = datetime(2026, 5, 8, 2, 14, tzinfo=UTC)

    DeviceStatus(
        id=device_id,
        label="Office plug",
        type="plug",
        description=None,
        current_severity=None,
        open_anomaly_count=0,
        last_seen=None,
    )
    AnomalyEventItem(
        id=123,
        device_id=device_id,
        device_label="Office plug",
        device_type="plug",
        scored_at=scored_at,
        anomaly_score=-0.23,
        event_severity="high",
        event_status="open",
        anomaly_reason=None,
        model_config_name="full_c003_e100",
        temperature_reading_id=None,
    )
    DeviceAnomalyEventItem(
        id=123,
        scored_at=scored_at,
        anomaly_score=-0.23,
        event_severity="high",
        event_status="open",
        anomaly_reason=None,
        temperature_reading_id=None,
    )


def test_decimal_values_are_converted_to_json_number_types() -> None:
    assert decimal_to_float(Decimal("22.50")) == 22.5
    assert format_reading({"temperature": Decimal("22.50"), "humidity": None}) == {
        "temperature": 22.5,
        "humidity": None,
    }


def test_device_status_statement_joins_anomalies_and_reading_sources() -> None:
    compiled = compile_statement(build_device_status_statement())

    assert "FROM devices" in compiled
    assert "anomaly_events" in compiled
    assert "temperature_readings" in compiled
    assert "energy_readings" in compiled
    assert "event_status = " in compiled
    assert "prediction = " in compiled
    assert "greatest" in compiled.lower()


def test_anomaly_events_statement_filters_and_joins_devices() -> None:
    compiled = compile_statement(
        build_anomaly_events_statement(
            limit=50,
            offset=0,
            status="open",
            severity="high",
            scored_since=datetime(2026, 5, 8, tzinfo=UTC),
        )
    )

    assert "JOIN devices ON devices.id = anomaly_events.device_id" in compiled
    assert "anomaly_events.prediction = " in compiled
    assert "anomaly_events.event_status = " in compiled
    assert "anomaly_events.event_severity = " in compiled
    assert "ORDER BY anomaly_events.scored_at DESC, anomaly_events.id DESC" in compiled


def test_summary_statement_counts_low_or_null_severity() -> None:
    compiled = compile_statement(build_summary_statement(datetime(2026, 5, 8, tzinfo=UTC)))

    assert "count(anomaly_events.id)" in compiled
    assert "anomaly_events.event_severity IS NULL" in compiled
    assert "count(DISTINCT anomaly_events.device_id)" in compiled
    assert "anomaly_events.event_status = " in compiled


def test_device_anomaly_events_statement_filters_device_and_sorts_newest_first() -> None:
    compiled = compile_statement(
        build_device_anomaly_events_statement(
            device_id=uuid4(),
            limit=100,
            offset=0,
            status="all",
            scored_since=datetime(2026, 5, 8, tzinfo=UTC),
        )
    )

    assert "anomaly_events.device_id = " in compiled
    assert "anomaly_events.event_status = " not in compiled
    assert "ORDER BY anomaly_events.scored_at DESC, anomaly_events.id DESC" in compiled


def test_reading_statements_filter_by_device_time_and_sort_ascending() -> None:
    device_id = uuid4()
    read_since = datetime(2026, 5, 8, tzinfo=UTC)
    temp_compiled = compile_statement(
        build_temperature_readings_statement(device_id=device_id, read_since=read_since, limit=2000)
    )
    energy_compiled = compile_statement(
        build_energy_readings_statement(device_id=device_id, read_since=read_since, limit=2000)
    )

    assert "temperature_readings.device_id = " in temp_compiled
    assert "temperature_readings.ts >= " in temp_compiled
    assert "ORDER BY temperature_readings.ts ASC, temperature_readings.id ASC" in temp_compiled
    assert "energy_readings.device_id = " in energy_compiled
    assert "energy_readings.ts >= " in energy_compiled
    assert "ORDER BY energy_readings.ts ASC, energy_readings.id ASC" in energy_compiled
