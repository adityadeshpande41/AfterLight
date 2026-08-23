from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class ActionItem(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "action_items"

    incident_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # Urgent, Important, Routine
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Open"
    )  # Open, In progress, Complete
    due: Mapped[str] = mapped_column(String(50), nullable=False)
    proof_description: Mapped[str] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    incident = relationship("Incident", back_populates="action_items")
