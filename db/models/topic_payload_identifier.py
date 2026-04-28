# db/models/topic_payload_identifier.py
from sqlalchemy import BigInteger, Column, Text
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base


class TopicPayloadIdentifier(Base):
    __tablename__ = "topic_payload_identifier"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    topic = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)
    type = Column(Text, nullable=True)

    def __repr__(self):
        return f"<TopicPayloadIdentifier id={self.id} topic={self.topic} type={self.type}>"
