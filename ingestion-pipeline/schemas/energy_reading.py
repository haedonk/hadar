# schemas/energy_reading.py
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EnergyReadingBase(BaseModel):
    device_id: UUID
    load_group_id: Optional[UUID] = None
    ts: datetime
    power_watts: Optional[Decimal] = None
    energy_kwh: Optional[Decimal] = None
    voltage_volts: Optional[Decimal] = None
    current_amps: Optional[Decimal] = None
    power_factor: Optional[Decimal] = None
    linkquality: Optional[int] = None
    source: str = "zigbee2mqtt"


class EnergyReadingCreate(EnergyReadingBase):
    pass


class EnergyReadingUpdate(BaseModel):
    load_group_id: Optional[UUID] = None
    power_watts: Optional[Decimal] = None
    energy_kwh: Optional[Decimal] = None
    voltage_volts: Optional[Decimal] = None
    current_amps: Optional[Decimal] = None
    power_factor: Optional[Decimal] = None
    linkquality: Optional[int] = None


class EnergyReading(EnergyReadingBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
