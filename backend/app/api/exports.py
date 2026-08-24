"""Export endpoints — generate downloadable reports."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ActionItem, EvidenceItem, Incident, ScoreSnapshot, Venue

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/incidents/{incident_id}")
async def export_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    """Export a full incident report as JSON (downloadable)."""
    if incident_id.startswith("INC-"):
        stmt = select(Incident).where(Incident.ref_code == incident_id)
    else:
        stmt = select(Incident).where(Incident.id == incident_id)

    incident = (await db.execute(stmt)).scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Get related data
    evidence = (await db.execute(
        select(EvidenceItem).where(EvidenceItem.incident_id == incident.id)
    )).scalars().all()

    actions = (await db.execute(
        select(ActionItem).where(ActionItem.incident_id == incident.id)
    )).scalars().all()

    report = {
        "export_type": "incident_report",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "incident": {
            "ref_code": incident.ref_code,
            "title": incident.title,
            "type": incident.incident_type,
            "severity": incident.severity,
            "status": incident.status,
            "location": incident.location,
            "occurred_at": incident.occurred_at.isoformat(),
            "people": incident.people.split(",") if incident.people else [],
            "summary": incident.summary,
            "evidence_completeness": incident.evidence_completeness,
        },
        "evidence": [
            {
                "label": e.label,
                "kind": e.kind,
                "status": e.status,
                "detail": e.detail,
            }
            for e in evidence
        ],
        "corrective_actions": [
            {
                "title": a.title,
                "owner": a.owner,
                "priority": a.priority,
                "status": a.status,
                "due": a.due,
                "proof": a.proof_description,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            }
            for a in actions
        ],
    }

    content = json.dumps(report, indent=2)
    filename = f"{incident.ref_code}_report.json"

    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/venues/{venue_id}/score")
async def export_score_history(venue_id: str, db: AsyncSession = Depends(get_db)):
    """Export score history as JSON (downloadable)."""
    venue_stmt = select(Venue).where(
        (Venue.slug == venue_id) if len(venue_id) < 36 else (Venue.id == venue_id)
    )
    venue = (await db.execute(venue_stmt)).scalar_one_or_none()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    snapshots = (await db.execute(
        select(ScoreSnapshot)
        .where(ScoreSnapshot.venue_id == venue.id)
        .order_by(ScoreSnapshot.calculated_at.asc())
    )).scalars().all()

    report = {
        "export_type": "score_history",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "venue": {"name": venue.name, "slug": venue.slug},
        "current_score": snapshots[-1].score if snapshots else None,
        "history": [
            {
                "score": s.score,
                "risk_index": s.risk_index,
                "factors": s.factors,
                "calculated_at": s.calculated_at.isoformat(),
            }
            for s in snapshots
        ],
    }

    content = json.dumps(report, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{venue.slug}_score_history.json"'},
    )
