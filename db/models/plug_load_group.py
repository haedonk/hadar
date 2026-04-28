# db/models/plug_load_group.py
from sqlalchemy import Column, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class PlugLoadGroup(Base):
    __tablename__ = "plug_load_group"

    device_id = Column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    load_group_id = Column(
        UUID(as_uuid=True), ForeignKey("load_groups.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    assigned_by = Column(Text, nullable=True)
    assignment_note = Column(Text, nullable=True)

    # Relationships
    device = relationship("Device", back_populates="current_assignment")
    load_group = relationship("LoadGroup", back_populates="current_devices")

    __table_args__ = (Index("idx_device_load_group_group", "load_group_id"),)

    def __repr__(self):
        return (
            f"<PlugLoadGroup device_id={self.device_id} "
            f"load_group_id={self.load_group_id} assigned_at={self.assigned_at}>"
        )
