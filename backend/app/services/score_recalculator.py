"""
Real-time score recalculation.

Called after any state change that affects the score:
- Action completed
- Evidence uploaded/verified
- Incident confirmed
- Pattern detected

Creates a new ScoreSnapshot with full factor breakdown.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActionItem, EvidenceItem, Incident, ScoreSnapshot, Venue
from app.services.scoring import IncidentInput, VenueRiskInput, calculate_score


async def recalculate_venue_score(venue_id: str, db: AsyncSession) -> ScoreSnapshot:
    """
    Recalculate the Savings Score for a venue based on current data.

    Creates and persists a new ScoreSnapshot.
    Returns the new snapshot.
    """
    # Load venue
    venue = (await db.execute(
        select(Venue).where(Venue.id == venue_id)
    )).scalar_one_or_none()
    if not venue:
        raise ValueError(f"Venue not found: {venue_id}")

    # Load incidents (last 90 days)
    now = datetime.now(timezone.utc)
    incidents = (await db.execute(
        select(Incident).where(Incident.venue_id == venue_id)
    )).scalars().all()

    # Build incident inputs for scoring
    incident_inputs = [
        IncidentInput(severity=i.severity, occurred_at=i.occurred_at)
        for i in incidents
    ]

    # Calculate evidence completeness across all active incidents
    all_evidence = []
    for incident in incidents:
        evidence_items = (await db.execute(
            select(EvidenceItem).where(EvidenceItem.incident_id == incident.id)
        )).scalars().all()
        all_evidence.extend(evidence_items)

    total_evidence = len(all_evidence)
    verified_evidence = len([e for e in all_evidence if e.status == "Verified"])
    evidence_completeness = (verified_evidence / total_evidence * 100) if total_evidence > 0 else 100.0

    # Calculate action completion
    all_actions = []
    for incident in incidents:
        actions = (await db.execute(
            select(ActionItem).where(ActionItem.incident_id == incident.id)
        )).scalars().all()
        all_actions.extend(actions)

    total_actions = len(all_actions)
    completed_actions = len([a for a in all_actions if a.status == "Complete"])
    open_ratio = (total_actions - completed_actions) / total_actions if total_actions > 0 else 0.0

    # Detect patterns (3+ incidents at same location in 60 days)
    from datetime import timedelta
    recent_incidents = [i for i in incidents if (now - i.occurred_at).days <= 60]
    locations = [i.location.split("·")[0].strip().lower() for i in recent_incidents]
    repeat_pattern = any(locations.count(loc) >= 3 for loc in set(locations))

    # Build input and calculate
    risk_input = VenueRiskInput(
        capacity=venue.capacity,
        incidents=incident_inputs,
        evidence_completeness_pct=evidence_completeness,
        open_action_ratio=open_ratio,
        verified_controls=completed_actions,
        repeat_pattern_detected=repeat_pattern,
    )

    factors = calculate_score(risk_input, now=now)

    # Create new snapshot
    snapshot = ScoreSnapshot(
        venue_id=venue.id,
        score=factors.savings_score,
        risk_index=factors.risk_index,
        factors=factors.to_dict(),
        calculated_at=now,
    )
    db.add(snapshot)
    await db.flush()

    return snapshot
