"""Action item endpoints — read + write."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ActionItem, Incident, Venue
from app.schemas.actions import ActionItemResponse, ActionListResponse, UpdateActionRequest

router = APIRouter(tags=["actions"])


@router.get("/venues/{venue_id}/actions", response_model=ActionListResponse)
async def list_venue_actions(venue_id: str, db: AsyncSession = Depends(get_db)):
    venue_stmt = select(Venue).where(
        (Venue.slug == venue_id) if len(venue_id) < 36 else (Venue.id == venue_id)
    )
    venue = (await db.execute(venue_stmt)).scalar_one_or_none()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    incident_ids_stmt = select(Incident.id).where(Incident.venue_id == venue.id)
    incident_ids = (await db.execute(incident_ids_stmt)).scalars().all()

    if not incident_ids:
        return ActionListResponse(actions=[])

    result = await db.execute(
        select(ActionItem).where(ActionItem.incident_id.in_(incident_ids))
    )
    actions = result.scalars().all()

    return ActionListResponse(actions=actions)


@router.patch("/actions/{action_id}", response_model=ActionItemResponse)
async def update_action(
    action_id: str,
    body: UpdateActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update an action item's status or proof description."""
    result = await db.execute(
        select(ActionItem).where(ActionItem.id == action_id)
    )
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if body.status is not None:
        action.status = body.status
        if body.status == "Complete":
            action.completed_at = datetime.now(timezone.utc)
    if body.proof_description is not None:
        action.proof_description = body.proof_description

    await db.commit()
    await db.refresh(action)

    return ActionItemResponse.model_validate(action)
