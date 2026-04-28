# schemas/load_group_member.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LoadGroupMemberBase(BaseModel):
    load_group_id: UUID
    appliance_id: UUID


class LoadGroupMemberCreate(LoadGroupMemberBase):
    pass


class LoadGroupMemberUpdate(BaseModel):
    removed_at: Optional[datetime] = None


class LoadGroupMember(LoadGroupMemberBase):
    added_at: datetime
    removed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
