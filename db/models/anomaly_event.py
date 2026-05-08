# db/models/anomaly_event.py
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, UUID

from .base import Base


class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    temperature_reading_id = Column(
        BigInteger,
        ForeignKey("temperature_readings.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )

    model_run_id = Column(Text, nullable=False)
    model_config_name = Column(Text, nullable=False)
    model_trained_at = Column(DateTime(timezone=True), nullable=True)

    scored_at = Column(DateTime(timezone=True), nullable=False)
    prediction = Column(SmallInteger, nullable=False)
    anomaly_score = Column(DOUBLE_PRECISION, nullable=False)
    anomaly_reason = Column(Text, nullable=True)

    event_status = Column(Text, nullable=False, server_default="open")
    event_severity = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "temperature_reading_id",
            "model_run_id",
            "model_config_name",
            name="anomaly_events_identity_uq",
        ),
        CheckConstraint("prediction IN (-1, 1)", name="anomaly_events_prediction_chk"),
        CheckConstraint(
            "event_status IN ('open', 'acknowledged', 'resolved')",
            name="anomaly_events_event_status_chk",
        ),
        CheckConstraint(
            "event_severity IS NULL OR event_severity IN ('low', 'medium', 'high')",
            name="anomaly_events_event_severity_chk",
        ),
        Index("idx_anomaly_events_device_scored_at", "device_id", "scored_at"),
        Index(
            "idx_anomaly_events_open_scored_at",
            "scored_at",
            postgresql_where=text("event_status = 'open'"),
        ),
        Index("idx_anomaly_events_model_run", "model_run_id"),
    )

    def __repr__(self):
        return (
            f"<AnomalyEvent id={self.id} device_id={self.device_id} "
            f"reading_id={self.temperature_reading_id} score={self.anomaly_score}>"
        )
