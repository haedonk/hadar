# db/models/device_rename.py
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class DeviceRename(Base):
    __tablename__ = "device_rename"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    from_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    to_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    notes = Column(Text, nullable=True)

    # Relationships
    from_device = relationship("Device", foreign_keys=[from_id], back_populates="renames_from")
    to_device = relationship("Device", foreign_keys=[to_id], back_populates="renames_to")

    def __repr__(self):
        return f"<DeviceRename id={self.id} from_id={self.from_id} to_id={self.to_id} created_at={self.created_at}>"
