# schemas/device_rename.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeviceRenameBase(BaseModel):
    from_id: UUID
    to_id: UUID
    notes: Optional[str] = None


class DeviceRenameCreate(DeviceRenameBase):
    pass


class DeviceRenameUpdate(BaseModel):
    notes: Optional[str] = None


class DeviceRename(DeviceRenameBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
