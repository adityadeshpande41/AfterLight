from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class Incident(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "incidents"

    venue_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("venues.id"), nullable=False, index=True
    )
    ref_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )  # e.g. INC-1042
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    incident_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # Low, Moderate, High
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Draft"
    )
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    people: Mapped[str] = mapped_column(
        Text, nullable=True
    )  # comma-separated for now
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_completeness: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # 0-100

    # Relationships
    venue = relationship("Venue", back_populates="incidents")
    evidence_items = relationship(
        "EvidenceItem", back_populates="incident", lazy="selectin"
    )
    action_items = relationship(
        "ActionItem", back_populates="incident", lazy="selectin"
    )
