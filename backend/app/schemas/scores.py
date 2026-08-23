"""Pydantic response schemas for scores."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class ScoreSnapshotResponse(BaseModel):
    id: uuid.UUID
    venue_id: uuid.UUID
    score: float
    risk_index: float
    factors: dict
    calculated_at: datetime

    model_config = {"from_attributes": True}


class ScoreHistoryResponse(BaseModel):
    snapshots: list[ScoreSnapshotResponse]
