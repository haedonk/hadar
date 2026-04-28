# schemas/temperature_reading.py
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TemperatureReadingBase(BaseModel):
    device_id: UUID
    ts: datetime
    battery: Optional[Decimal] = None
    humidity: Optional[Decimal] = None
    pressure: Optional[Decimal] = None
    temperature: Optional[Decimal] = None
    linkquality: Optional[int] = None
    source: str = "zigbee2mqtt"


class TemperatureReadingCreate(TemperatureReadingBase):
    pass


class TemperatureReadingUpdate(BaseModel):
    battery: Optional[Decimal] = None
    humidity: Optional[Decimal] = None
    pressure: Optional[Decimal] = None
    temperature: Optional[Decimal] = None
    linkquality: Optional[int] = None


class TemperatureReading(TemperatureReadingBase):
    id: int
    ts: datetime

    model_config = ConfigDict(from_attributes=True)
