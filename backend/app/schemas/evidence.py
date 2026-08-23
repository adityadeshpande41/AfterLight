"""Pydantic request/response schemas for evidence items."""

import uuid

from pydantic import BaseModel


class EvidenceItemResponse(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    label: str
    kind: str
    status: str
    detail: str | None
    object_key: str | None
    file_hash: str | None

    model_config = {"from_attributes": True}


class EvidenceListResponse(BaseModel):
    evidence: list[EvidenceItemResponse]


class UpdateEvidenceRequest(BaseModel):
    """Request body for updating an evidence item."""
    status: str | None = None
    detail: str | None = None
