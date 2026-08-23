"""Pydantic request/response schemas for incidents."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class IncidentResponse(BaseModel):
    id: uuid.UUID
    venue_id: uuid.UUID
    ref_code: str
    title: str
    incident_type: str
    severity: str
    status: str
    location: str
    occurred_at: datetime
    people: list[str]
    summary: str
    evidence_completeness: int

    model_config = {"from_attributes": True}


class IncidentListResponse(BaseModel):
    incidents: list[IncidentResponse]


class CreateIncidentRequest(BaseModel):
    """Request body for creating a new incident."""
    title: str
    incident_type: str
    severity: str = "Moderate"
    location: str
    occurred_at: datetime | None = None
    people: list[str] = []
    summary: str
