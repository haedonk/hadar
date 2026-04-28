# schemas/event_log.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EventLog(BaseModel):
    id: Optional[int]
    event_type: str
    description: str
    timestamp: datetime

    class Config:
        orm_mode = True
