# db/models/plug_load_group_history.py
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class PlugLoadGroupHistory(Base):
    __tablename__ = "plug_load_group_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    load_group_id = Column(UUID(as_uuid=True), ForeignKey("load_groups.id", ondelete="RESTRICT"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), nullable=False)
    unassigned_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    changed_by = Column(Text, nullable=True)
    change_reason = Column(Text, nullable=True)

    # Relationships
    device = relationship("Device", back_populates="assignment_history")
    load_group = relationship("LoadGroup", back_populates="device_history")

    __table_args__ = (Index("idx_device_load_group_hist_device_time", "device_id", "unassigned_at"),)

    def __repr__(self):
        return (
            f"<PlugLoadGroupHistory id={self.id} device_id={self.device_id} "
            f"load_group_id={self.load_group_id} assigned_at={self.assigned_at} "
            f"unassigned_at={self.unassigned_at}>"
        )
