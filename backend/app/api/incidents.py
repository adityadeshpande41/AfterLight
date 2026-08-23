"""Incident endpoints — read + write."""

import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Incident, Venue
from app.schemas.incidents import (
    CreateIncidentRequest,
    IncidentListResponse,
    IncidentResponse,
)

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
    if incident_id.startswith("INC-"):
        stmt = select(Incident).where(Incident.ref_code == incident_id)
    else:
        stmt = select(Incident).where(Incident.id == incident_id)

    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return _to_response(incident)


@router.post("/venues/{venue_id}/incidents", response_model=IncidentResponse, status_code=201)
async def create_incident(
    venue_id: str,
    body: CreateIncidentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new incident for a venue."""
    venue_stmt = select(Venue).where(
        (Venue.slug == venue_id) if len(venue_id) < 36 else (Venue.id == venue_id)
    )
    venue = (await db.execute(venue_stmt)).scalar_one_or_none()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    # Generate next ref_code
    max_code = (
        await db.execute(
            select(func.max(Incident.ref_code))
        )
    ).scalar_one_or_none()
    if max_code:
        next_num = int(max_code.split("-")[1]) + 1
    else:
        next_num = 1001
    ref_code = f"INC-{next_num}"

    incident = Incident(
        venue_id=venue.id,
        ref_code=ref_code,
        title=body.title,
        incident_type=body.incident_type,
        severity=body.severity,
        status="Draft",
        location=body.location,
        occurred_at=body.occurred_at or datetime.now(timezone.utc),
        people=",".join(body.people) if body.people else "",
        summary=body.summary,
        evidence_completeness=0,
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    return _to_response(incident)
