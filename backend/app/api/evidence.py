"""Evidence item endpoints — read + write."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import EvidenceItem, Incident, Venue
from app.schemas.evidence import EvidenceItemResponse, EvidenceListResponse, UpdateEvidenceRequest

router = APIRouter(tags=["evidence"])


@router.get("/venues/{venue_id}/evidence", response_model=EvidenceListResponse)
async def list_venue_evidence(venue_id: str, db: AsyncSession = Depends(get_db)):
    venue_stmt = select(Venue).where(
        (Venue.slug == venue_id) if len(venue_id) < 36 else (Venue.id == venue_id)
    )
    venue = (await db.execute(venue_stmt)).scalar_one_or_none()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    incident_ids_stmt = select(Incident.id).where(Incident.venue_id == venue.id)
    incident_ids = (await db.execute(incident_ids_stmt)).scalars().all()

    if not incident_ids:
        return EvidenceListResponse(evidence=[])

    result = await db.execute(
        select(EvidenceItem).where(EvidenceItem.incident_id.in_(incident_ids))
    )
    evidence = result.scalars().all()

    return EvidenceListResponse(evidence=evidence)


@router.patch("/evidence/{evidence_id}", response_model=EvidenceItemResponse)
async def update_evidence(
    evidence_id: str,
    body: UpdateEvidenceRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update an evidence item's status or detail."""
    result = await db.execute(
        select(EvidenceItem).where(EvidenceItem.id == evidence_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Evidence item not found")

    if body.status is not None:
        item.status = body.status
    if body.detail is not None:
        item.detail = body.detail

    await db.commit()
    await db.refresh(item)

    return EvidenceItemResponse.model_validate(item)
