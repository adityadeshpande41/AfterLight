from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class Venue(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "venues"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    venue_type: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    incidents = relationship("Incident", back_populates="venue", lazy="selectin")
    score_snapshots = relationship(
        "ScoreSnapshot", back_populates="venue", lazy="selectin"
    )
