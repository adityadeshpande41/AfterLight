from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class EvidenceItem(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "evidence_items"

    incident_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(100), nullable=False)  # Video, Photo, Document, Statement
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Missing"
    )  # Verified, Missing, Pending review
    detail: Mapped[str] = mapped_column(Text, nullable=True)
    object_key: Mapped[str | None] = mapped_column(String(500), nullable=True)  # S3 key
    file_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Relationships
    incident = relationship("Incident", back_populates="evidence_items")
