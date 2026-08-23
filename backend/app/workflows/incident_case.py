"""
LangGraph Incident Case Supervisor.

A typed state graph that coordinates specialized agents:
1. Evidence Agent — checks evidence completeness
2. Pattern Agent — SQL analytics on incident history
3. Mitigation Agent — drafts action plan using LLM
4. Validator — deterministic schema/citation validation

The supervisor routes through agents sequentially, not as a free-form swarm.
"""

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.workflows.agents.evidence_agent import evidence_agent
from app.workflows.agents.mitigation_agent import mitigation_agent
from app.workflows.agents.pattern_agent import pattern_agent
from app.workflows.agents.validator import validator_agent


class IncidentCaseState(TypedDict):
    """Shared state flowing through the workflow."""

    incident_id: str
    # Populated by data loader
    incident: dict | None
    evidence_items: list[dict]
    venue: dict | None
    # Populated by Evidence Agent
    evidence_assessment: dict | None
    findings: list[dict]
    # Populated by Pattern Agent
    pattern_analysis: dict | None
    # Populated by Mitigation Agent
    action_plan_draft: list[dict]
    # Populated by Validator
    validation_result: dict | None
    is_valid: bool
    needs_human_review: bool
    # Audit
    errors: list[str]


async def load_incident_data(state: IncidentCaseState) -> IncidentCaseState:
    """Load incident, evidence, and venue data from the database."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import settings
    from app.models import EvidenceItem, Incident, Venue

    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # Load incident
        result = await session.execute(
            select(Incident).where(Incident.id == state["incident_id"])
        )
        incident = result.scalar_one_or_none()
        if not incident:
            return {**state, "errors": ["Incident not found"]}

        # Load evidence
        ev_result = await session.execute(
            select(EvidenceItem).where(EvidenceItem.incident_id == incident.id)
        )
        evidence_items = ev_result.scalars().all()

        # Load venue
        venue_result = await session.execute(
            select(Venue).where(Venue.id == incident.venue_id)
        )
        venue = venue_result.scalar_one_or_none()

    await engine.dispose()

    return {
        **state,
        "incident": {
            "id": str(incident.id),
            "ref_code": incident.ref_code,
            "title": incident.title,
            "type": incident.incident_type,
            "severity": incident.severity,
            "location": incident.location,
            "occurred_at": incident.occurred_at.isoformat(),
            "summary": incident.summary,
            "people": incident.people.split(",") if incident.people else [],
        },
        "evidence_items": [
            {
                "id": str(e.id),
                "label": e.label,
                "kind": e.kind,
                "status": e.status,
                "detail": e.detail,
            }
            for e in evidence_items
        ],
        "venue": {
            "id": str(venue.id),
            "name": venue.name,
            "capacity": venue.capacity,
            "location": venue.location,
        }
        if venue
        else None,
    }


def should_continue(state: IncidentCaseState) -> str:
    """Route based on validation result."""
    if state.get("errors"):
        return "end"
    if state.get("is_valid"):
        return "end"
    if state.get("needs_human_review"):
        return "end"
    return "end"


def build_incident_case_graph() -> StateGraph:
    """Construct the LangGraph state graph for incident case processing."""
    graph = StateGraph(IncidentCaseState)

    # Add nodes
    graph.add_node("load_data", load_incident_data)
    graph.add_node("evidence_agent", evidence_agent)
    graph.add_node("pattern_agent", pattern_agent)
    graph.add_node("mitigation_agent", mitigation_agent)
    graph.add_node("validator", validator_agent)

    # Define edges — sequential pipeline
    graph.set_entry_point("load_data")
    graph.add_edge("load_data", "evidence_agent")
    graph.add_edge("evidence_agent", "pattern_agent")
    graph.add_edge("pattern_agent", "mitigation_agent")
    graph.add_edge("mitigation_agent", "validator")
    graph.add_edge("validator", END)

    return graph


# Compile the graph
incident_case_graph = build_incident_case_graph().compile()


async def run_incident_case(incident_id: str) -> dict:
    """Execute the full incident case workflow."""
    initial_state: IncidentCaseState = {
        "incident_id": incident_id,
        "incident": None,
        "evidence_items": [],
        "venue": None,
        "evidence_assessment": None,
        "findings": [],
        "pattern_analysis": None,
        "action_plan_draft": [],
        "validation_result": None,
        "is_valid": False,
        "needs_human_review": False,
        "errors": [],
    }

    result = await incident_case_graph.ainvoke(initial_state)

    # Store results in database
    await _persist_workflow_results(result)

    return result


async def _persist_workflow_results(state: IncidentCaseState):
    """Save workflow findings and audit trail to the database."""
    from datetime import datetime, timezone

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import settings
    from app.models import AuditEvent, Incident

    if not state.get("incident"):
        return

    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # Update incident status
        result = await session.execute(
            select(Incident).where(Incident.id == state["incident_id"])
        )
        incident = result.scalar_one_or_none()
        if incident and state.get("is_valid"):
            incident.status = "Ready for review"

        # Create audit event
        import uuid

        audit = AuditEvent(
            id=uuid.uuid4(),
            venue_id=uuid.UUID(state["venue"]["id"]) if state.get("venue") else None,
            entity_type="incident",
            entity_id=uuid.UUID(state["incident_id"]),
            action="workflow_complete",
            actor="incident_case_supervisor",
            meta={
                "findings_count": len(state.get("findings", [])),
                "actions_proposed": len(state.get("action_plan_draft", [])),
                "is_valid": state.get("is_valid", False),
                "needs_human_review": state.get("needs_human_review", False),
                "errors": state.get("errors", []),
            },
        )
        session.add(audit)
        await session.commit()

    await engine.dispose()
