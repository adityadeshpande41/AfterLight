"""Agent runs endpoint — shows real workflow execution history."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AuditEvent

router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])


class AgentRunResponse(BaseModel):
    id: str
    venue_id: str | None
    entity_type: str
    entity_id: str
    action: str
    actor: str
    meta: dict | None
    created_at: str

    model_config = {"from_attributes": True}


class AgentRunsListResponse(BaseModel):
    runs: list[AgentRunResponse]


@router.get("", response_model=AgentRunsListResponse)
async def list_agent_runs(db: AsyncSession = Depends(get_db)):
    """List all workflow-related audit events (agent runs)."""
    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.action.in_(["workflow_complete", "plan_approved", "plan_rejected", "plan_needs_edits"]))
        .order_by(AuditEvent.created_at.desc())
        .limit(20)
    )
    events = result.scalars().all()

    return AgentRunsListResponse(
        runs=[
            AgentRunResponse(
                id=str(e.id),
                venue_id=str(e.venue_id) if e.venue_id else None,
                entity_type=e.entity_type,
                entity_id=str(e.entity_id),
                action=e.action,
                actor=e.actor,
                meta=e.meta,
                created_at=e.created_at.isoformat(),
            )
            for e in events
        ]
    )
