# schemas/device.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeviceBase(BaseModel):
    device_label: str
    device_type: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    device_label: Optional[str] = None
    device_type: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    renamed_at: Optional[datetime] = None


class Device(DeviceBase):
    id: UUID
    created_at: datetime
    renamed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
