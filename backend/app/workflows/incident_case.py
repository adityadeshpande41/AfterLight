"""
LangGraph Incident Case Supervisor — Real Multi-Agent Architecture.

Graph structure:
                    ┌─────────────────┐
                    │   load_data     │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
    ┌─────────▼─────────┐       ┌──────────▼──────────┐
    │  evidence_agent   │       │   pattern_agent     │
    └─────────┬─────────┘       └──────────┬──────────┘
              │                             │
              └──────────────┬──────────────┘
                             │
                    ┌────────▼────────┐
                    │ playbook_agent  │  (RAG over pgvector)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │mitigation_agent │  (LLM — structured output)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    validator    │  (deterministic)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
               ┌───│  route_decision │───┐
               │   └──────────────────┘   │
               │                          │
        valid / retry_exhausted      needs_retry
               │                          │
               ▼                          ▼
             END                  mitigation_agent
                                  (with feedback)
"""

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.workflows.agents.evidence_agent import evidence_agent
from app.workflows.agents.mitigation_agent import mitigation_agent
from app.workflows.agents.pattern_agent import pattern_agent
from app.workflows.agents.playbook_agent import playbook_agent
from app.workflows.agents.validator import validator_agent


class IncidentCaseState(TypedDict):
    """Shared state flowing through the workflow."""

    incident_id: str
    # Data layer
    incident: dict | None
    evidence_items: list[dict]
    venue: dict | None
    # Evidence Agent output
    evidence_assessment: dict | None
    findings: list[dict]
    # Pattern Agent output
    pattern_analysis: dict | None
    # Playbook Agent output (RAG)
    playbook_citations: list[dict]
    # Mitigation Agent output (LLM)
    action_plan_draft: list[dict]
    # Validator output
    validation_result: dict | None
    is_valid: bool
    needs_human_review: bool
    # Retry tracking
    retry_count: int
    validation_feedback: str | None
    # Errors
    errors: list[str]
    # Trace (internal, not serialized to response directly)
    _trace: Any


async def load_incident_data(state: IncidentCaseState) -> IncidentCaseState:
    """Load incident, evidence, and venue data from the database."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import settings
    from app.models import EvidenceItem, Incident, Venue

    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(
            select(Incident).where(Incident.id == state["incident_id"])
        )
        incident = result.scalar_one_or_none()
        if not incident:
            return {**state, "errors": ["Incident not found"]}

        ev_result = await session.execute(
            select(EvidenceItem).where(EvidenceItem.incident_id == incident.id)
        )
        evidence_items = ev_result.scalars().all()

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


async def parallel_analysis(state: IncidentCaseState) -> IncidentCaseState:
    """
    Run Evidence Agent and Pattern Agent in parallel.
    Both are independent — neither depends on the other's output.
    """
    import asyncio

    # Run both agents concurrently
    evidence_task = asyncio.create_task(evidence_agent(state))
    pattern_task = asyncio.create_task(pattern_agent(state))

    evidence_result, pattern_result = await asyncio.gather(evidence_task, pattern_task)

    # Merge results
    return {
        **state,
        "evidence_assessment": evidence_result.get("evidence_assessment"),
        "findings": evidence_result.get("findings", []),
        "pattern_analysis": pattern_result.get("pattern_analysis"),
    }


def route_after_validation(state: IncidentCaseState) -> str:
    """
    Conditional routing after validation:
    - If valid → END
    - If invalid and retry_count < 1 → retry mitigation with feedback
    - If invalid and retry exhausted → END (human review)
    """
    if state.get("errors"):
        return "end"
    if state.get("is_valid"):
        return "end"
    if state.get("retry_count", 0) < 1:
        return "retry_mitigation"
    # Retry exhausted — route to human review
    return "end"


async def prepare_retry(state: IncidentCaseState) -> IncidentCaseState:
    """Prepare validation feedback for the Mitigation Agent retry."""
    validation_result = state.get("validation_result", {})
    errors = validation_result.get("errors", [])

    feedback = (
        f"Your previous action plan had validation errors. "
        f"Fix these issues: {'; '.join(errors)}. "
        f"Ensure every action has: title, owner (a role), priority (Urgent/Important/Routine), "
        f"due_description, required_proof, and a citation from the findings."
    )

    return {
        **state,
        "retry_count": state.get("retry_count", 0) + 1,
        "validation_feedback": feedback,
        "action_plan_draft": [],  # Clear for retry
    }


def build_incident_case_graph() -> StateGraph:
    """Construct the LangGraph state graph for incident case processing."""
    graph = StateGraph(IncidentCaseState)

    # Nodes
    graph.add_node("load_data", load_incident_data)
    graph.add_node("parallel_analysis", parallel_analysis)
    graph.add_node("playbook_agent", playbook_agent)
    graph.add_node("mitigation_agent", mitigation_agent)
    graph.add_node("validator", validator_agent)
    graph.add_node("prepare_retry", prepare_retry)

    # Edges — the flow
    graph.set_entry_point("load_data")
    graph.add_edge("load_data", "parallel_analysis")
    graph.add_edge("parallel_analysis", "playbook_agent")
    graph.add_edge("playbook_agent", "mitigation_agent")
    graph.add_edge("mitigation_agent", "validator")

    # Conditional routing after validation
    graph.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "end": END,
            "retry_mitigation": "prepare_retry",
        },
    )
    graph.add_edge("prepare_retry", "mitigation_agent")

    return graph


# Compile the graph
incident_case_graph = build_incident_case_graph().compile()


async def run_incident_case(incident_id: str) -> dict:
    """Execute the full incident case workflow."""
    from app.workflows.tracing import WorkflowTrace
    import uuid as uuid_mod

    trace = WorkflowTrace(
        workflow_id=str(uuid_mod.uuid4())[:8],
        incident_id=incident_id,
    )

    initial_state: IncidentCaseState = {
        "incident_id": incident_id,
        "incident": None,
        "evidence_items": [],
        "venue": None,
        "evidence_assessment": None,
        "findings": [],
        "pattern_analysis": None,
        "playbook_citations": [],
        "action_plan_draft": [],
        "validation_result": None,
        "is_valid": False,
        "needs_human_review": False,
        "retry_count": 0,
        "validation_feedback": None,
        "errors": [],
        "_trace": trace,
    }

    result = await incident_case_graph.ainvoke(initial_state)

    # Persist results
    await _persist_workflow_results(result)

    # Attach trace to result (remove internal _trace key)
    result.pop("_trace", None)
    result["trace"] = trace.to_dict()

    return result


async def _persist_workflow_results(state: IncidentCaseState):
    """Save workflow findings and audit trail to the database."""
    import uuid

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
        if incident:
            incident.status = "Ready for review"

        # Create audit event
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
                "playbook_citations": len(state.get("playbook_citations", [])),
                "is_valid": state.get("is_valid", False),
                "needs_human_review": state.get("needs_human_review", False),
                "retry_count": state.get("retry_count", 0),
                "errors": state.get("errors", []),
            },
        )
        session.add(audit)
        await session.commit()

    await engine.dispose()
