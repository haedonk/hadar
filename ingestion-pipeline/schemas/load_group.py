# schemas/load_group.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LoadGroupBase(BaseModel):
    name: str
    location: Optional[str] = None
    notes: Optional[str] = None


class LoadGroupCreate(LoadGroupBase):
    pass


class LoadGroupUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class LoadGroup(LoadGroupBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
