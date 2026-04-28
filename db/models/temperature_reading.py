# db/models/temperature_reading.py
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class TemperatureReading(Base):
    __tablename__ = "temperature_readings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    battery = Column(Numeric(3, 0), nullable=True)
    humidity = Column(Numeric(5, 2), nullable=True)
    pressure = Column(Numeric(7, 2), nullable=True)
    temperature = Column(Numeric(5, 2), nullable=True)
    linkquality = Column(Integer, nullable=True)
    source = Column(Text, default="zigbee2mqtt")

    # Relationships
    device = relationship("Device", back_populates="temperature_readings")

    __table_args__ = (Index("idx_temp_device_time", "device_id", "ts"),)

    def __repr__(self):
        return f"<TemperatureReading id={self.id} device_id={self.device_id} ts={self.ts}>"
