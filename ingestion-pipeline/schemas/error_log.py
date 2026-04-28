# schemas/error_log.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ErrorLogBase(BaseModel):
    source: str
    error_type: str
    message: str
    details: Optional[str] = None
    device_id: Optional[UUID] = None
    topic: Optional[str] = None


class ErrorLogCreate(ErrorLogBase):
    pass


class ErrorLogUpdate(BaseModel):
    source: Optional[str] = None
    error_type: Optional[str] = None
    message: Optional[str] = None
    details: Optional[str] = None
    device_id: Optional[UUID] = None
    topic: Optional[str] = None


class ErrorLog(ErrorLogBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
