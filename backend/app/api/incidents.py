"""Incident endpoints — read-only."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Incident, Venue
from app.schemas.incidents import IncidentListResponse, IncidentResponse

router = APIRouter(tags=["incidents"])


def _to_response(incident: Incident) -> IncidentResponse:
    return IncidentResponse(
        id=incident.id,
        venue_id=incident.venue_id,
        ref_code=incident.ref_code,
        title=incident.title,
        incident_type=incident.incident_type,
        severity=incident.severity,
        status=incident.status,
        location=incident.location,
        occurred_at=incident.occurred_at,
        people=incident.people.split(",") if incident.people else [],
        summary=incident.summary,
        evidence_completeness=incident.evidence_completeness,
    )


@router.get("/venues/{venue_id}/incidents", response_model=IncidentListResponse)
async def list_venue_incidents(venue_id: str, db: AsyncSession = Depends(get_db)):
    # Resolve venue
    venue_stmt = select(Venue).where(
        (Venue.slug == venue_id) if len(venue_id) < 36 else (Venue.id == venue_id)
    )
    venue = (await db.execute(venue_stmt)).scalar_one_or_none()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    result = await db.execute(
        select(Incident)
        .where(Incident.venue_id == venue.id)
        .order_by(Incident.occurred_at.desc())
    )
    incidents = result.scalars().all()

    return IncidentListResponse(incidents=[_to_response(i) for i in incidents])


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    # Support lookup by UUID or ref_code
    if incident_id.startswith("INC-"):
        stmt = select(Incident).where(Incident.ref_code == incident_id)
    else:
        stmt = select(Incident).where(Incident.id == incident_id)

    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return _to_response(incident)
