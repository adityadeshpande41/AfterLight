"""Score endpoints — read-only."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ScoreSnapshot, Venue
from app.schemas.scores import ScoreHistoryResponse, ScoreSnapshotResponse

router = APIRouter(tags=["scores"])


@router.get("/venues/{venue_id}/score", response_model=ScoreSnapshotResponse)
async def get_current_score(venue_id: str, db: AsyncSession = Depends(get_db)):
    venue_stmt = select(Venue).where(
        (Venue.slug == venue_id) if len(venue_id) < 36 else (Venue.id == venue_id)
    )
    venue = (await db.execute(venue_stmt)).scalar_one_or_none()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    result = await db.execute(
        select(ScoreSnapshot)
        .where(ScoreSnapshot.venue_id == venue.id)
        .order_by(ScoreSnapshot.calculated_at.desc())
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        raise HTTPException(status_code=404, detail="No score data available")

    return ScoreSnapshotResponse.model_validate(snapshot)


@router.get("/venues/{venue_id}/score/history", response_model=ScoreHistoryResponse)
async def get_score_history(venue_id: str, db: AsyncSession = Depends(get_db)):
    venue_stmt = select(Venue).where(
        (Venue.slug == venue_id) if len(venue_id) < 36 else (Venue.id == venue_id)
    )
    venue = (await db.execute(venue_stmt)).scalar_one_or_none()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    result = await db.execute(
        select(ScoreSnapshot)
        .where(ScoreSnapshot.venue_id == venue.id)
        .order_by(ScoreSnapshot.calculated_at.asc())
    )
    snapshots = result.scalars().all()

    return ScoreHistoryResponse(
        snapshots=[ScoreSnapshotResponse.model_validate(s) for s in snapshots]
    )
