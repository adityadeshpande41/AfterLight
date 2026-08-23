"""Workflow trigger and status endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Incident

router = APIRouter(prefix="/workflows", tags=["workflows"])


class WorkflowTriggerResponse(BaseModel):
    status: str
    incident_id: str
    message: str


class WorkflowRunResponse(BaseModel):
    status: str
    incident_id: str
    findings: list[dict]
    action_plan_draft: list[dict]
    evidence_assessment: dict | None
    pattern_analysis: dict | None
    validation_result: dict | None
    is_valid: bool
    needs_human_review: bool
    errors: list[str]


@router.post("/incidents/{incident_id}/analyze", response_model=WorkflowRunResponse)
async def trigger_incident_workflow(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger the incident case workflow synchronously (for demo).

    In production, this would queue a Celery task and return immediately.
    For the demo, we run it inline so the response includes results.
    """
    # Verify incident exists
    if incident_id.startswith("INC-"):
        stmt = select(Incident).where(Incident.ref_code == incident_id)
    else:
        stmt = select(Incident).where(Incident.id == incident_id)

    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Run the workflow inline (synchronous for demo)
    from app.workflows.incident_case import run_incident_case

    workflow_result = await run_incident_case(str(incident.id))

    return WorkflowRunResponse(
        status="complete",
        incident_id=str(incident.id),
        findings=workflow_result.get("findings", []),
        action_plan_draft=workflow_result.get("action_plan_draft", []),
        evidence_assessment=workflow_result.get("evidence_assessment"),
        pattern_analysis=workflow_result.get("pattern_analysis"),
        validation_result=workflow_result.get("validation_result"),
        is_valid=workflow_result.get("is_valid", False),
        needs_human_review=workflow_result.get("needs_human_review", True),
        errors=workflow_result.get("errors", []),
    )
