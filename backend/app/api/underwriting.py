"""Underwriting workflow endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Venue

router = APIRouter(prefix="/underwriting", tags=["underwriting"])


class UnderwritingResponse(BaseModel):
    venue: dict | None
    historical_risk: dict | None
    control_status: dict | None
    guidelines: list[dict]
    draft: dict | None
    posture: str | None
    forced_referral: bool
    referral_reasons: list[str]
    errors: list[str]


@router.post("/venues/{venue_id}/generate", response_model=UnderwritingResponse)
async def generate_underwriting_draft(
    venue_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an underwriting posture draft for a venue.

    Runs the full underwriting workflow:
    1. Historical risk analysis (SQL)
    2. Control verification (SQL)
    3. Guideline retrieval (RAG)
    4. Draft composition (LLM)
    5. Guardrail validation (deterministic referral rules)
    """
    # Verify venue exists
    venue_stmt = select(Venue).where(
        (Venue.slug == venue_id) if len(venue_id) < 36 else (Venue.id == venue_id)
    )
    venue = (await db.execute(venue_stmt)).scalar_one_or_none()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    from app.workflows.underwriting import run_underwriting_workflow

    result = await run_underwriting_workflow(venue_id)

    return UnderwritingResponse(
        venue=result.get("venue"),
        historical_risk=result.get("historical_risk"),
        control_status=result.get("control_status"),
        guidelines=result.get("guidelines", []),
        draft=result.get("draft"),
        posture=result.get("posture"),
        forced_referral=result.get("forced_referral", False),
        referral_reasons=result.get("referral_reasons", []),
        errors=result.get("errors", []),
    )
