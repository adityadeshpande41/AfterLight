"""Pydantic response schemas for evidence items."""

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
