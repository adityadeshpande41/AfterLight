"""Venue endpoints — read-only."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ScoreSnapshot, Venue
from app.schemas.venues import VenueListResponse, VenueResponse

router = APIRouter(prefix="/venues", tags=["venues"])


def _enrich_venue(venue: Venue, snapshots: list[ScoreSnapshot]) -> VenueResponse:
    """Add computed score/risk fields to a venue response."""
    # Get the two most recent snapshots for this venue
    venue_snaps = sorted(
        [s for s in snapshots if s.venue_id == venue.id],
        key=lambda s: s.calculated_at,
        reverse=True,
    )
    current_score = venue_snaps[0].score if venue_snaps else None
    prev_score = venue_snaps[1].score if len(venue_snaps) > 1 else None
    delta = round(current_score - prev_score, 1) if current_score and prev_score else 0

    # Determine risk level and review status
    if current_score is not None:
        if current_score < 60:
            risk, review = "High", "Urgent review"
        elif current_score < 75:
            risk, review = "Moderate", "Monitoring"
        else:
            risk, review = "Low", "Healthy"
    else:
        risk, review = None, None

    return VenueResponse(
        id=venue.id,
        name=venue.name,
        slug=venue.slug,
        venue_type=venue.venue_type,
        location=venue.location,
        capacity=venue.capacity,
        created_at=venue.created_at,
        score=current_score,
        delta=delta,
        risk=risk,
        review=review,
    )


@router.get("", response_model=VenueListResponse)
async def list_venues(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Venue))
    venues = result.scalars().all()

    snap_result = await db.execute(select(ScoreSnapshot))
    snapshots = snap_result.scalars().all()

    return VenueListResponse(
        venues=[_enrich_venue(v, snapshots) for v in venues]
    )


@router.get("/{venue_id}", response_model=VenueResponse)
async def get_venue(venue_id: str, db: AsyncSession = Depends(get_db)):
    # Support both UUID and slug lookup
    stmt = select(Venue).where(
        (Venue.slug == venue_id) | (Venue.id == venue_id)
        if len(venue_id) < 36
        else (Venue.id == venue_id)
    )
    result = await db.execute(stmt)
    venue = result.scalar_one_or_none()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    snap_result = await db.execute(
        select(ScoreSnapshot).where(ScoreSnapshot.venue_id == venue.id)
    )
    snapshots = snap_result.scalars().all()

    return _enrich_venue(venue, snapshots)
