"""Pydantic request/response schemas for action items."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class ActionItemResponse(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    title: str
    owner: str
    priority: str
    status: str
    due: str
    proof_description: str | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class ActionListResponse(BaseModel):
    actions: list[ActionItemResponse]


class UpdateActionRequest(BaseModel):
    """Request body for updating an action item."""
    status: str | None = None
    proof_description: str | None = None
