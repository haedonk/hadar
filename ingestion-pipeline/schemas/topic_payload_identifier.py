# schemas/topic_payload_identifier.py
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class TopicPayloadIdentifierBase(BaseModel):
    topic: str
    payload: Dict[str, Any]
    type: Optional[str] = None


class TopicPayloadIdentifierCreate(TopicPayloadIdentifierBase):
    pass


class TopicPayloadIdentifierUpdate(BaseModel):
    topic: str | None = None
    payload: Dict[str, Any] | None = None
    type: str | None = None


class TopicPayloadIdentifier(TopicPayloadIdentifierBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
