# db/models/error_log.py
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source = Column(Text, nullable=False)
    error_type = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True)
    topic = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    device = relationship("Device", back_populates="error_logs")

    def __repr__(self):
        return f"<ErrorLog id={self.id} source={self.source} error_type={self.error_type} created_at={self.created_at}>"
