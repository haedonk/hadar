# db/models/load_group.py
import uuid

from sqlalchemy import Column, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class LoadGroup(Base):
    __tablename__ = "load_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, unique=True, nullable=False, index=True)
    location = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    energy_readings = relationship("EnergyReading", back_populates="load_group")
    members = relationship("LoadGroupMember", back_populates="load_group", cascade="all, delete-orphan")
    current_devices = relationship("PlugLoadGroup", back_populates="load_group", cascade="all, delete-orphan")
    device_history = relationship("PlugLoadGroupHistory", back_populates="load_group")

    def __repr__(self):
        return f"<LoadGroup id={self.id} name={self.name}>"
