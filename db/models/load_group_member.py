# db/models/load_group_member.py
from sqlalchemy import Column, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class LoadGroupMember(Base):
    __tablename__ = "load_group_members"

    load_group_id = Column(
        UUID(as_uuid=True), ForeignKey("load_groups.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    appliance_id = Column(
        UUID(as_uuid=True), ForeignKey("appliances.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    added_at = Column(DateTime(timezone=True), primary_key=True, nullable=False, server_default=func.now())
    removed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    load_group = relationship("LoadGroup", back_populates="members")
    appliance = relationship("Appliance", back_populates="group_memberships")

    __table_args__ = (
        Index("idx_group_members_active", "load_group_id", postgresql_where=(Column("removed_at").is_(None))),
        Index(
            "uq_appliance_one_active_group",
            "appliance_id",
            unique=True,
            postgresql_where=(Column("removed_at").is_(None)),
        ),
    )

    def __repr__(self):
        return (
            f"<LoadGroupMember load_group_id={self.load_group_id} "
            f"appliance_id={self.appliance_id} added_at={self.added_at}>"
        )
