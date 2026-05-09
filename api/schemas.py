from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

Severity = Literal["high", "medium", "low"]
EventStatus = Literal["open", "acknowledged", "resolved"]
StatusFilter = Literal["open", "acknowledged", "resolved", "all"]


class DeviceStatus(BaseModel):
    id: UUID
    label: str
    type: str
    description: str
    current_severity: Severity | None
    open_anomaly_count: int
    last_seen: datetime | None


class AnomalyEventItem(BaseModel):
    id: int
    device_id: UUID
    device_label: str
    device_type: str
    scored_at: datetime
    anomaly_score: float
    event_severity: Severity | None
    event_status: EventStatus
    anomaly_reason: str | None
    model_config_name: str
    temperature_reading_id: int


class AnomalyEventPage(BaseModel):
    total: int
    events: list[AnomalyEventItem]


class Summary(BaseModel):
    open_anomaly_count: int
    critical_count: int
    warning_count: int
    low_count: int
    affected_device_count: int
    window_hours: int


class DeviceAnomalyEventItem(BaseModel):
    id: int
    scored_at: datetime
    anomaly_score: float
    event_severity: Severity | None
    event_status: EventStatus
    anomaly_reason: str | None
    temperature_reading_id: int


class TemperatureReadingItem(BaseModel):
    id: int
    ts: datetime
    temperature: float | None
    humidity: float | None
    battery: float | None


class EnergyReadingItem(BaseModel):
    id: int
    ts: datetime
    power_watts: float | None
    energy_kwh: float | None
    voltage_volts: float | None
    current_amps: float | None


class TemperatureReadingsResponse(BaseModel):
    type: Literal["temperature"]
    readings: list[TemperatureReadingItem]


class EnergyReadingsResponse(BaseModel):
    type: Literal["energy"]
    readings: list[EnergyReadingItem]


class HealthResponse(BaseModel):
    status: Literal["ok"]
