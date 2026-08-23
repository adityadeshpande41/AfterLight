"""
Seed script — populates the database with demo data.
Run: python seed.py
"""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models import ActionItem, AuditEvent, EvidenceItem, Incident, ScoreSnapshot, Venue

# Fixed UUIDs so relationships are stable across re-seeds
MOONLIGHT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
HARBOR_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
JUNCTION_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")

INC_1042_ID = uuid.UUID("aaaa1042-1042-1042-1042-104210421042")
INC_1027_ID = uuid.UUID("aaaa1027-1027-1027-1027-102710271027")
INC_1010_ID = uuid.UUID("aaaa1010-1010-1010-1010-101010101010")


def dt(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


VENUES = [
    Venue(
        id=MOONLIGHT_ID,
        name="Moonlight Club",
        slug="moonlight",
        venue_type="Nightclub",
        location="Williamsburg, Brooklyn",
        capacity=650,
    ),
    Venue(
        id=HARBOR_ID,
        name="Harbor Rooftop",
        slug="harbor",
        venue_type="Rooftop bar",
        location="Manhattan",
        capacity=300,
    ),
    Venue(
        id=JUNCTION_ID,
        name="The Junction Hall",
        slug="junction",
        venue_type="Live music venue",
        location="Brooklyn",
        capacity=900,
    ),
]

INCIDENTS = [
    Incident(
        id=INC_1042_ID,
        venue_id=MOONLIGHT_ID,
        ref_code="INC-1042",
        title="Slip-and-fall near main entrance",
        incident_type="Injury",
        severity="High",
        status="Ready for review",
        location="Main entrance · Camera 3",
        occurred_at=dt(2026, 8, 23, 1, 20),
        people="Emergency services,Security",
        summary="Guest slipped on pooled water at the main entrance during peak egress. Security responded within two minutes and EMS assessed the guest on site.",
        evidence_completeness=67,
    ),
    Incident(
        id=INC_1027_ID,
        venue_id=MOONLIGHT_ID,
        ref_code="INC-1027",
        title="Guest injury at entrance mat",
        incident_type="Injury",
        severity="Moderate",
        status="Action plan active",
        location="Main entrance",
        occurred_at=dt(2026, 8, 9, 0, 44),
        people="Security",
        summary="A guest reported ankle pain after the edge of the entrance mat lifted during the late-night rush.",
        evidence_completeness=82,
    ),
    Incident(
        id=INC_1010_ID,
        venue_id=MOONLIGHT_ID,
        ref_code="INC-1010",
        title="Crowd surge at front doors",
        incident_type="Crowd management",
        severity="Moderate",
        status="Closed",
        location="Main entrance",
        occurred_at=dt(2026, 7, 28, 1, 56),
        people="Security,Manager",
        summary="A short crowd surge formed during last call. Door staffing was adjusted and the entry lane was re-marked.",
        evidence_completeness=94,
    ),
]

EVIDENCE_ITEMS = [
    EvidenceItem(
        id=uuid.UUID("eeee0001-0001-0001-0001-000100010001"),
        incident_id=INC_1042_ID,
        label="Camera 3 preservation confirmation",
        kind="Video",
        status="Missing",
        detail="Main entrance camera. Retention window closes in 18 hours.",
    ),
    EvidenceItem(
        id=uuid.UUID("eeee0002-0002-0002-0002-000200020002"),
        incident_id=INC_1042_ID,
        label="Witness statement · Door lead",
        kind="Statement",
        status="Pending review",
        detail="Uploaded by Jordan Lee. Signature is still outstanding.",
    ),
    EvidenceItem(
        id=uuid.UUID("eeee0003-0003-0003-0003-000300030003"),
        incident_id=INC_1042_ID,
        label="EMS response record",
        kind="Document",
        status="Verified",
        detail="Incident number and arrival time match the report.",
    ),
    EvidenceItem(
        id=uuid.UUID("eeee0004-0004-0004-0004-000400040004"),
        incident_id=INC_1042_ID,
        label="Entrance condition photo",
        kind="Photo",
        status="Verified",
        detail="Timestamped images show pooled water near the threshold.",
    ),
]

ACTION_ITEMS = [
    ActionItem(
        id=uuid.UUID("cccc0001-0001-0001-0001-000100010001"),
        incident_id=INC_1042_ID,
        title="Preserve Camera 3 footage",
        owner="Maya Chen",
        priority="Urgent",
        status="Open",
        due="Due today",
        proof_description="Video export required",
    ),
    ActionItem(
        id=uuid.UUID("cccc0002-0002-0002-0002-000200020002"),
        incident_id=INC_1042_ID,
        title="Collect witness statement from door team",
        owner="Jordan Lee",
        priority="Urgent",
        status="In progress",
        due="Due tomorrow",
        proof_description="1 of 2 statements",
    ),
    ActionItem(
        id=uuid.UUID("cccc0003-0003-0003-0003-000300030003"),
        incident_id=INC_1027_ID,
        title="Replace and anchor entrance mat",
        owner="Facilities",
        priority="Important",
        status="Complete",
        due="Sep 02",
        proof_description="Photo uploaded Aug 12",
        completed_at=dt(2026, 8, 12),
    ),
    ActionItem(
        id=uuid.UUID("cccc0004-0004-0004-0004-000400040004"),
        incident_id=INC_1042_ID,
        title="Add wet-floor response checkpoint",
        owner="Maya Chen",
        priority="Important",
        status="Open",
        due="Sep 05",
        proof_description="Checklist not started",
    ),
]

SCORE_SNAPSHOTS = [
    ScoreSnapshot(venue_id=MOONLIGHT_ID, score=74, risk_index=26, factors={"evidence": 78, "actions": 65, "response": 80, "cadence": 72}, calculated_at=dt(2026, 3, 1)),
    ScoreSnapshot(venue_id=MOONLIGHT_ID, score=73, risk_index=27, factors={"evidence": 76, "actions": 63, "response": 79, "cadence": 71}, calculated_at=dt(2026, 4, 1)),
    ScoreSnapshot(venue_id=MOONLIGHT_ID, score=71, risk_index=29, factors={"evidence": 74, "actions": 60, "response": 78, "cadence": 70}, calculated_at=dt(2026, 5, 1)),
    ScoreSnapshot(venue_id=MOONLIGHT_ID, score=69, risk_index=31, factors={"evidence": 72, "actions": 56, "response": 76, "cadence": 69}, calculated_at=dt(2026, 6, 1)),
    ScoreSnapshot(venue_id=MOONLIGHT_ID, score=66, risk_index=34, factors={"evidence": 70, "actions": 50, "response": 74, "cadence": 68}, calculated_at=dt(2026, 7, 1)),
    ScoreSnapshot(venue_id=MOONLIGHT_ID, score=58, risk_index=42, factors={"evidence": 67, "actions": 42, "response": 82, "cadence": 74}, calculated_at=dt(2026, 8, 1)),
    # Harbor Rooftop
    ScoreSnapshot(venue_id=HARBOR_ID, score=78, risk_index=22, factors={"evidence": 85, "actions": 72, "response": 80, "cadence": 76}, calculated_at=dt(2026, 8, 1)),
    # Junction Hall
    ScoreSnapshot(venue_id=JUNCTION_ID, score=86, risk_index=14, factors={"evidence": 90, "actions": 84, "response": 88, "cadence": 82}, calculated_at=dt(2026, 8, 1)),
]


async def seed():
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # Clear existing data (order matters for FK constraints)
        await session.execute(text("DELETE FROM score_snapshots"))
        await session.execute(text("DELETE FROM audit_events"))
        await session.execute(text("DELETE FROM action_items"))
        await session.execute(text("DELETE FROM evidence_items"))
        await session.execute(text("DELETE FROM incidents"))
        await session.execute(text("DELETE FROM venues"))

        # Insert
        session.add_all(VENUES)
        await session.flush()

        session.add_all(INCIDENTS)
        await session.flush()

        session.add_all(EVIDENCE_ITEMS)
        session.add_all(ACTION_ITEMS)
        session.add_all(SCORE_SNAPSHOTS)

        await session.commit()

    await engine.dispose()
    print("✓ Seeded: 3 venues, 3 incidents, 4 evidence items, 4 actions, 8 score snapshots")


if __name__ == "__main__":
    asyncio.run(seed())
