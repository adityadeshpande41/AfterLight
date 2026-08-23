from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKey


class ScoreSnapshot(Base, UUIDPrimaryKey):
    __tablename__ = "score_snapshots"

    venue_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("venues.id"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)  # SavingsScore 0-100
    risk_index: Mapped[float] = mapped_column(Float, nullable=False)  # RiskIndex 0-100
    factors: Mapped[dict] = mapped_column(JSONB, nullable=False)  # factor-level breakdown
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    venue = relationship("Venue", back_populates="score_snapshots")
