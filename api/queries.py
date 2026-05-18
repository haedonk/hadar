from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Select, case, desc, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.anomaly_event import AnomalyEvent
from db.models.device import Device
from db.models.energy_reading import EnergyReading
from db.models.temperature_reading import TemperatureReading

SEVERITY_BY_RANK = {3: "high", 2: "medium", 1: "low"}


def utc_now() -> datetime:
    return datetime.now(UTC)


def decimal_to_float(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def severity_rank_expression():
    return case(
        (AnomalyEvent.event_severity == "high", 3),
        (AnomalyEvent.event_severity == "medium", 2),
        (AnomalyEvent.event_severity == "low", 1),
        else_=0,
    )


def severity_from_rank(rank: int | None) -> str | None:
    return SEVERITY_BY_RANK.get(rank or 0)


def build_device_status_statement(
    device_id: UUID | None = None, *, temperature_only: bool = False
) -> Select:
    open_events = (
        select(
            AnomalyEvent.device_id.label("device_id"),
            func.count(AnomalyEvent.id).label("open_anomaly_count"),
            func.max(severity_rank_expression()).label("severity_rank"),
        )
        .where(AnomalyEvent.event_status == "open", AnomalyEvent.prediction == -1)
        .group_by(AnomalyEvent.device_id)
        .subquery()
    )
    latest_temperature = (
        select(
            TemperatureReading.device_id.label("device_id"),
            func.max(TemperatureReading.ts).label("last_temperature_seen"),
        )
        .group_by(TemperatureReading.device_id)
        .subquery()
    )
    latest_energy = (
        select(
            EnergyReading.device_id.label("device_id"),
            func.max(EnergyReading.ts).label("last_energy_seen"),
        )
        .group_by(EnergyReading.device_id)
        .subquery()
    )

    statement = (
        select(
            Device.id.label("id"),
            Device.device_label.label("label"),
            Device.device_type.label("type"),
            Device.description.label("description"),
            func.coalesce(open_events.c.open_anomaly_count, 0).label("open_anomaly_count"),
            open_events.c.severity_rank.label("severity_rank"),
            func.greatest(
                latest_temperature.c.last_temperature_seen,
                latest_energy.c.last_energy_seen,
            ).label("last_seen"),
        )
        .outerjoin(open_events, open_events.c.device_id == Device.id)
        .outerjoin(latest_temperature, latest_temperature.c.device_id == Device.id)
        .outerjoin(latest_energy, latest_energy.c.device_id == Device.id)
        .order_by(Device.device_label)
    )
    if device_id is not None:
        statement = statement.where(Device.id == device_id)
    if temperature_only:
        # Dashboard surfaces environmental sensors only; energy plugs are excluded.
        statement = statement.where(Device.device_type != "plug")
    return statement


def format_device_status(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "label": row["label"],
        "type": row["type"],
        "description": row["description"],
        "current_severity": severity_from_rank(row["severity_rank"]),
        "open_anomaly_count": int(row["open_anomaly_count"] or 0),
        "last_seen": row["last_seen"],
    }


async def fetch_devices(session: AsyncSession) -> list[dict[str, Any]]:
    result = await session.execute(build_device_status_statement(temperature_only=True))
    return [format_device_status(dict(row)) for row in result.mappings().all()]


async def fetch_device(session: AsyncSession, device_id: UUID) -> dict[str, Any] | None:
    result = await session.execute(build_device_status_statement(device_id))
    row = result.mappings().first()
    if row is None:
        return None
    return format_device_status(dict(row))


def anomaly_filters(
    *,
    status: str,
    severity: str | None,
    scored_since: datetime,
    device_id: UUID | None = None,
) -> list[Any]:
    filters = [AnomalyEvent.prediction == -1, AnomalyEvent.scored_at >= scored_since]
    if status != "all":
        filters.append(AnomalyEvent.event_status == status)
    if severity is not None:
        filters.append(AnomalyEvent.event_severity == severity)
    if device_id is not None:
        filters.append(AnomalyEvent.device_id == device_id)
    return filters


def build_anomaly_events_statement(
    *,
    limit: int,
    offset: int,
    status: str,
    severity: str | None,
    scored_since: datetime,
) -> Select:
    return (
        select(
            AnomalyEvent.id,
            AnomalyEvent.device_id,
            Device.device_label,
            Device.device_type,
            AnomalyEvent.scored_at,
            AnomalyEvent.anomaly_score,
            AnomalyEvent.event_severity,
            AnomalyEvent.event_status,
            AnomalyEvent.anomaly_reason,
            AnomalyEvent.model_config_name,
            AnomalyEvent.temperature_reading_id,
        )
        .join(Device, Device.id == AnomalyEvent.device_id)
        .where(*anomaly_filters(status=status, severity=severity, scored_since=scored_since))
        .order_by(desc(AnomalyEvent.scored_at), desc(AnomalyEvent.id))
        .limit(limit)
        .offset(offset)
    )


def build_anomaly_events_count_statement(*, status: str, severity: str | None, scored_since: datetime) -> Select:
    return select(func.count(AnomalyEvent.id)).where(
        *anomaly_filters(status=status, severity=severity, scored_since=scored_since)
    )


def format_anomaly_event(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "device_id": row["device_id"],
        "device_label": row["device_label"],
        "device_type": row["device_type"],
        "scored_at": row["scored_at"],
        "anomaly_score": float(row["anomaly_score"]),
        "event_severity": row["event_severity"],
        "event_status": row["event_status"],
        "anomaly_reason": row["anomaly_reason"],
        "model_config_name": row["model_config_name"],
        "temperature_reading_id": row["temperature_reading_id"],
    }


async def fetch_anomaly_events(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    status: str,
    severity: str | None,
    hours: int,
) -> dict[str, Any]:
    scored_since = utc_now() - timedelta(hours=hours)
    total_result = await session.execute(
        build_anomaly_events_count_statement(status=status, severity=severity, scored_since=scored_since)
    )
    rows_result = await session.execute(
        build_anomaly_events_statement(
            limit=limit,
            offset=offset,
            status=status,
            severity=severity,
            scored_since=scored_since,
        )
    )
    return {
        "total": int(total_result.scalar_one()),
        "events": [format_anomaly_event(dict(row)) for row in rows_result.mappings().all()],
    }


def build_summary_statement(scored_since: datetime) -> Select:
    return select(
        func.count(AnomalyEvent.id).label("open_anomaly_count"),
        func.coalesce(func.sum(case((AnomalyEvent.event_severity == "high", 1), else_=0)), 0).label("critical_count"),
        func.coalesce(func.sum(case((AnomalyEvent.event_severity == "medium", 1), else_=0)), 0).label("warning_count"),
        func.coalesce(
            func.sum(
                case(
                    (or_(AnomalyEvent.event_severity == "low", AnomalyEvent.event_severity.is_(None)), 1),
                    else_=0,
                )
            ),
            0,
        ).label("low_count"),
        func.count(distinct(AnomalyEvent.device_id)).label("affected_device_count"),
    ).where(
        AnomalyEvent.event_status == "open",
        AnomalyEvent.prediction == -1,
        AnomalyEvent.scored_at >= scored_since,
    )


async def fetch_summary(session: AsyncSession, *, window_hours: int = 24) -> dict[str, Any]:
    result = await session.execute(build_summary_statement(utc_now() - timedelta(hours=window_hours)))
    row = result.mappings().one()
    return {
        "open_anomaly_count": int(row["open_anomaly_count"] or 0),
        "critical_count": int(row["critical_count"] or 0),
        "warning_count": int(row["warning_count"] or 0),
        "low_count": int(row["low_count"] or 0),
        "affected_device_count": int(row["affected_device_count"] or 0),
        "window_hours": window_hours,
    }


def build_device_anomaly_events_statement(
    *,
    device_id: UUID,
    limit: int,
    offset: int,
    status: str,
    scored_since: datetime,
) -> Select:
    return (
        select(
            AnomalyEvent.id,
            AnomalyEvent.scored_at,
            AnomalyEvent.anomaly_score,
            AnomalyEvent.event_severity,
            AnomalyEvent.event_status,
            AnomalyEvent.anomaly_reason,
            AnomalyEvent.temperature_reading_id,
        )
        .where(*anomaly_filters(status=status, severity=None, scored_since=scored_since, device_id=device_id))
        .order_by(desc(AnomalyEvent.scored_at), desc(AnomalyEvent.id))
        .limit(limit)
        .offset(offset)
    )


def format_device_anomaly_event(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "scored_at": row["scored_at"],
        "anomaly_score": float(row["anomaly_score"]),
        "event_severity": row["event_severity"],
        "event_status": row["event_status"],
        "anomaly_reason": row["anomaly_reason"],
        "temperature_reading_id": row["temperature_reading_id"],
    }


async def fetch_device_anomaly_events(
    session: AsyncSession,
    *,
    device_id: UUID,
    limit: int,
    offset: int,
    status: str,
    days: int,
) -> list[dict[str, Any]] | None:
    if await fetch_device(session, device_id) is None:
        return None
    result = await session.execute(
        build_device_anomaly_events_statement(
            device_id=device_id,
            limit=limit,
            offset=offset,
            status=status,
            scored_since=utc_now() - timedelta(days=days),
        )
    )
    return [format_device_anomaly_event(dict(row)) for row in result.mappings().all()]


def build_temperature_readings_statement(*, device_id: UUID, read_since: datetime, limit: int) -> Select:
    return (
        select(
            TemperatureReading.id,
            TemperatureReading.ts,
            TemperatureReading.temperature,
            TemperatureReading.humidity,
            TemperatureReading.battery,
        )
        .where(TemperatureReading.device_id == device_id, TemperatureReading.ts >= read_since)
        .order_by(TemperatureReading.ts.asc(), TemperatureReading.id.asc())
        .limit(limit)
    )


def build_energy_readings_statement(*, device_id: UUID, read_since: datetime, limit: int) -> Select:
    return (
        select(
            EnergyReading.id,
            EnergyReading.ts,
            EnergyReading.power_watts,
            EnergyReading.energy_kwh,
            EnergyReading.voltage_volts,
            EnergyReading.current_amps,
        )
        .where(EnergyReading.device_id == device_id, EnergyReading.ts >= read_since)
        .order_by(EnergyReading.ts.asc(), EnergyReading.id.asc())
        .limit(limit)
    )


def format_reading(row: dict[str, Any]) -> dict[str, Any]:
    return {key: decimal_to_float(value) for key, value in row.items()}


async def fetch_device_readings(
    session: AsyncSession,
    *,
    device_id: UUID,
    days: int,
    limit: int,
) -> dict[str, Any] | None:
    device_result = await session.execute(select(Device.id, Device.device_type).where(Device.id == device_id))
    device = device_result.mappings().first()
    if device is None:
        return None

    read_since = utc_now() - timedelta(days=days)
    if device["device_type"] == "plug":
        result = await session.execute(
            build_energy_readings_statement(device_id=device_id, read_since=read_since, limit=limit)
        )
        return {"type": "energy", "readings": [format_reading(dict(row)) for row in result.mappings().all()]}

    result = await session.execute(
        build_temperature_readings_statement(device_id=device_id, read_since=read_since, limit=limit)
    )
    return {"type": "temperature", "readings": [format_reading(dict(row)) for row in result.mappings().all()]}
