# schemas/appliance.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ApplianceBase(BaseModel):
    name: str
    category: Optional[str] = None
    manufacturer: Optional[str] = None
    notes: Optional[str] = None


class ApplianceCreate(ApplianceBase):
    pass


class ApplianceUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    manufacturer: Optional[str] = None
    notes: Optional[str] = None


class Appliance(ApplianceBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
