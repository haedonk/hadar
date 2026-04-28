# schemas/plug_load_group.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PlugLoadGroupBase(BaseModel):
    plug_id: UUID
    load_group_id: UUID
    assigned_by: Optional[str] = None
    assignment_note: Optional[str] = None


class PlugLoadGroupCreate(PlugLoadGroupBase):
    pass


class PlugLoadGroupUpdate(BaseModel):
    load_group_id: Optional[UUID] = None
    assigned_by: Optional[str] = None
    assignment_note: Optional[str] = None


class PlugLoadGroup(PlugLoadGroupBase):
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)
