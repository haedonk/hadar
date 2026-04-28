# db/models/appliance.py
import uuid

from sqlalchemy import Column, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class Appliance(Base):
    __tablename__ = "appliances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, unique=True, nullable=False, index=True)
    category = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    manufacturer = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    group_memberships = relationship("LoadGroupMember", back_populates="appliance", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Appliance id={self.id} name={self.name}>"
