# schemas/plug_load_group_history.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PlugLoadGroupHistoryBase(BaseModel):
    plug_id: UUID
    load_group_id: UUID
    assigned_at: datetime
    changed_by: Optional[str] = None
    change_reason: Optional[str] = None


class PlugLoadGroupHistoryCreate(PlugLoadGroupHistoryBase):
    pass


class PlugLoadGroupHistory(PlugLoadGroupHistoryBase):
    id: int
    unassigned_at: datetime

    model_config = ConfigDict(from_attributes=True)
