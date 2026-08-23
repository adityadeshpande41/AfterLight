"""
Pattern Agent — SQL analytics on incident history.

Primarily deterministic. Detects frequency, severity, recurring patterns.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models import Incident


async def pattern_agent(state: dict) -> dict:
    """
    Analyze incident patterns for the venue.

    Outputs:
    - pattern_analysis: frequency, severity, recurring type/location/time patterns
    """
    incident = state.get("incident")
    venue = state.get("venue")

    if not incident or not venue:
        return {**state, "pattern_analysis": None}

    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # Get all incidents for this venue in the last 90 days
        result = await session.execute(
            select(Incident)
            .where(Incident.venue_id == venue["id"])
            .order_by(Incident.occurred_at.desc())
        )
        all_incidents = result.scalars().all()

    await engine.dispose()

    # Analyze patterns
    now = datetime.now(timezone.utc)
    incidents_60d = [
        i for i in all_incidents
        if (now - i.occurred_at).days <= 60
    ]
    incidents_30d = [
        i for i in all_incidents
        if (now - i.occurred_at).days <= 30
    ]

    # Location clustering
    location_counts: dict[str, int] = {}
    for i in all_incidents:
        loc = i.location.split("·")[0].strip().lower()
        location_counts[loc] = location_counts.get(loc, 0) + 1

    top_location = max(location_counts, key=location_counts.get) if location_counts else None
    location_repeat = location_counts.get(top_location, 0) >= 2 if top_location else False

    # Time-of-day clustering
    night_incidents = [
        i for i in incidents_60d
        if i.occurred_at.hour >= 23 or i.occurred_at.hour <= 3
    ]

    # Severity trend
    severities_recent = [i.severity for i in incidents_30d]
    has_high_recent = "High" in severities_recent

    # Determine if pattern detected
    pattern_detected = (
        len(incidents_60d) >= 3
        or (location_repeat and len(incidents_60d) >= 2)
        or (len(night_incidents) >= 2)
    )

    # Trend direction
    if len(incidents_30d) > len(incidents_60d) - len(incidents_30d):
        trend = "increasing"
    elif len(incidents_30d) == 0 and len(incidents_60d) > 0:
        trend = "decreasing"
    else:
        trend = "stable"

    pattern_analysis = {
        "pattern_detected": pattern_detected,
        "incidents_30d": len(incidents_30d),
        "incidents_60d": len(incidents_60d),
        "total_incidents": len(all_incidents),
        "trend": trend,
        "top_location": top_location,
        "location_repeat_count": location_counts.get(top_location, 0) if top_location else 0,
        "night_cluster_count": len(night_incidents),
        "has_high_severity_recent": has_high_recent,
        "supporting_incident_ids": [i.ref_code for i in incidents_60d[:5]],
        "summary": _build_summary(incidents_60d, top_location, night_incidents, trend),
    }

    return {**state, "pattern_analysis": pattern_analysis}


def _build_summary(
    incidents_60d: list,
    top_location: str | None,
    night_incidents: list,
    trend: str,
) -> str:
    """Build a human-readable pattern summary."""
    parts = []

    if len(incidents_60d) >= 3:
        parts.append(f"{len(incidents_60d)} incidents in the last 60 days")

    if top_location and len([i for i in incidents_60d if top_location in i.location.lower()]) >= 2:
        count = len([i for i in incidents_60d if top_location in i.location.lower()])
        parts.append(f"{count} incidents at the {top_location}")

    if len(night_incidents) >= 2:
        parts.append(f"{len(night_incidents)} incidents between midnight and 2 AM")

    if trend == "increasing":
        parts.append("frequency is increasing")

    return ". ".join(parts) + "." if parts else "No significant pattern detected."
