# db/models/energy_reading.py
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class EnergyReading(Base):
    __tablename__ = "energy_readings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    load_group_id = Column(
        UUID(as_uuid=True), ForeignKey("load_groups.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    ts = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    power_watts = Column(Numeric(10, 3), nullable=True)
    energy_kwh = Column(Numeric(12, 6), nullable=True)
    voltage_volts = Column(Numeric(6, 2), nullable=True)
    current_amps = Column(Numeric(6, 3), nullable=True)
    power_factor = Column(Numeric(4, 3), nullable=True)
    linkquality = Column(Integer, nullable=True)
    source = Column(Text, default="zigbee2mqtt")

    # Relationships
    device = relationship("Device", back_populates="energy_readings")
    load_group = relationship("LoadGroup", back_populates="energy_readings")

    __table_args__ = (
        Index("idx_energy_device_ts", "device_id", "ts"),
        Index("idx_energy_group_ts", "load_group_id", "ts"),
    )

    def __repr__(self):
        return f"<EnergyReading id={self.id} device_id={self.device_id} ts={self.ts}>"
