# db/models/device.py
import uuid

from sqlalchemy import Column, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_label = Column(Text, unique=True, nullable=False, index=True)
    device_type = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    renamed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    energy_readings = relationship("EnergyReading", back_populates="device", cascade="all, delete-orphan")
    temperature_readings = relationship("TemperatureReading", back_populates="device", cascade="all, delete-orphan")
    error_logs = relationship("ErrorLog", back_populates="device")
    current_assignment = relationship(
        "PlugLoadGroup", back_populates="device", uselist=False, cascade="all, delete-orphan"
    )
    assignment_history = relationship("PlugLoadGroupHistory", back_populates="device", cascade="all, delete-orphan")
    renames_from = relationship(
        "DeviceRename", foreign_keys="DeviceRename.from_id", back_populates="from_device", cascade="all, delete-orphan"
    )
    renames_to = relationship(
        "DeviceRename", foreign_keys="DeviceRename.to_id", back_populates="to_device", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Device id={self.id} label={self.device_label}>"
