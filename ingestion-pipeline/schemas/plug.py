# schemas/device.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PlugBase(BaseModel):
    plug_label: str
    notes: Optional[str] = None


class PlugCreate(PlugBase):
    pass


class PlugUpdate(BaseModel):
    plug_label: Optional[str] = None
    notes: Optional[str] = None
    last_seen: Optional[datetime] = None


class Plug(PlugBase):
    id: UUID
    created_at: datetime
    last_seen: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
