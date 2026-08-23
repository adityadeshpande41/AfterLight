"""Human review decisions on workflow-generated plans."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey


class PlanDecision(Base, UUIDPrimaryKey):
    __tablename__ = "plan_decisions"

    incident_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # approved, rejected, needs_edits
    reviewer: Mapped[str] = mapped_column(String(100), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_plan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # The plan at time of decision
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
