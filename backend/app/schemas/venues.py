"""Pydantic response schemas for venues."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class VenueResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    venue_type: str
    location: str
    capacity: int
    created_at: datetime

    # Computed fields populated by the API
    score: float | None = None
    delta: float | None = None
    risk: str | None = None
    review: str | None = None

    model_config = {"from_attributes": True}


class VenueListResponse(BaseModel):
    venues: list[VenueResponse]
