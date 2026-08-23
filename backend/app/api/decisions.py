"""Plan decision endpoints — human-in-the-loop approval/rejection."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ActionItem, AuditEvent, Incident, PlanDecision

router = APIRouter(prefix="/decisions", tags=["decisions"])


class CreateDecisionRequest(BaseModel):
    incident_id: str
    decision: str  # approved, rejected, needs_edits
    reviewer: str
    note: str | None = None
    action_plan: list[dict] | None = None


class DecisionResponse(BaseModel):
    id: str
    incident_id: str
    decision: str
    reviewer: str
    note: str | None
    decided_at: str

    model_config = {"from_attributes": True}


@router.post("", response_model=DecisionResponse, status_code=201)
async def create_decision(
    body: CreateDecisionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Record a human review decision on a workflow-generated plan.

    If approved:
    - The action plan items become real ActionItems in the database
    - The incident status updates to 'Action plan active'
    - An audit event is created

    If rejected/needs_edits:
    - The incident stays in review
    - An audit event records the decision
    """
    import uuid

    # Find the incident
    if body.incident_id.startswith("INC-"):
        stmt = select(Incident).where(Incident.ref_code == body.incident_id)
    else:
        stmt = select(Incident).where(Incident.id == body.incident_id)
    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Create the decision record
    decision = PlanDecision(
        incident_id=incident.id,
        decision=body.decision,
        reviewer=body.reviewer,
        note=body.note,
        action_plan=body.action_plan,
    )
    db.add(decision)

    # If approved, create real ActionItems from the plan
    if body.decision == "approved" and body.action_plan:
        for action_data in body.action_plan:
            action = ActionItem(
                incident_id=incident.id,
                title=action_data.get("title", ""),
                owner=action_data.get("owner", "Venue Manager"),
                priority=action_data.get("priority", "Important"),
                status="Open",
                due=action_data.get("due_description", "TBD"),
                proof_description=action_data.get("required_proof", ""),
            )
            db.add(action)
        incident.status = "Action plan active"

    elif body.decision == "rejected":
        incident.status = "Plan rejected"

    elif body.decision == "needs_edits":
        incident.status = "Needs edits"

    # Audit event
    audit = AuditEvent(
        id=uuid.uuid4(),
        venue_id=incident.venue_id,
        entity_type="incident",
        entity_id=incident.id,
        action=f"plan_{body.decision}",
        actor=body.reviewer,
        meta={"note": body.note, "action_count": len(body.action_plan) if body.action_plan else 0},
    )
    db.add(audit)

    await db.commit()
    await db.refresh(decision)

    return DecisionResponse(
        id=str(decision.id),
        incident_id=str(decision.incident_id),
        decision=decision.decision,
        reviewer=decision.reviewer,
        note=decision.note,
        decided_at=decision.decided_at.isoformat(),
    )
