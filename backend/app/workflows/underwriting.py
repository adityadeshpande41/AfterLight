"""
LangGraph Underwriting Plan Workflow.

Triggered by an internal user. Generates a structured underwriting
posture draft for a venue based on operational data.

Graph structure:
    load_venue_data
         ↓
    ┌────┴────┐  (parallel)
    │         │
historical  control_verification
    │         │
    └────┬────┘
         ↓
    guideline_agent (RAG)
         ↓
    draft_agent (LLM)
         ↓
    guardrail_validator (deterministic referral rules)
         ↓
       END
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from openai import OpenAI
from sqlalchemy import create_engine, text

from app.config import settings
from app.services.embeddings import get_embedding
from app.workflows.tools.rag_tools import RAG_TOOL_FUNCTIONS

from app.sync_db import SYNC_URL


class UnderwritingState(TypedDict):
    venue_id: str
    venue: dict | None
    # Historical Risk Agent output
    historical_risk: dict | None
    # Control Verification Agent output
    control_status: dict | None
    # Guideline Agent output (RAG)
    guidelines: list[dict]
    # Draft Agent output
    draft: dict | None
    # Guardrail Validator output
    posture: str | None  # favorable, conditional, refer, decline_review
    forced_referral: bool
    referral_reasons: list[str]
    # Meta
    errors: list[str]
    _trace: Any


async def load_venue_data(state: UnderwritingState) -> UnderwritingState:
    """Load venue metadata."""
    engine = create_engine(SYNC_URL)
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, name, slug, venue_type, location, capacity FROM venues WHERE slug = :slug OR id::text = :id"),
            {"slug": state["venue_id"], "id": state["venue_id"]},
        ).fetchone()
    engine.dispose()

    if not row:
        return {**state, "errors": ["Venue not found"]}

    return {
        **state,
        "venue": {
            "id": str(row[0]),
            "name": row[1],
            "slug": row[2],
            "type": row[3],
            "location": row[4],
            "capacity": row[5],
        },
    }


async def historical_risk_agent(state: UnderwritingState) -> UnderwritingState:
    """SQL analytics: incident frequency, severity, score trend."""
    venue = state.get("venue")
    if not venue:
        return state

    venue_uuid = venue["id"]
    engine = create_engine(SYNC_URL)

    with engine.connect() as conn:
        # Incident stats
        incidents = conn.execute(
            text("""SELECT ref_code, title, severity, occurred_at, status
                    FROM incidents WHERE venue_id = :vid
                    ORDER BY occurred_at DESC"""),
            {"vid": venue_uuid},
        ).fetchall()

        # Score history
        scores = conn.execute(
            text("""SELECT score, risk_index, factors, calculated_at
                    FROM score_snapshots WHERE venue_id = :vid
                    ORDER BY calculated_at DESC LIMIT 6"""),
            {"vid": venue_uuid},
        ).fetchall()

        # Action stats
        action_stats = conn.execute(
            text("""SELECT ai.status, COUNT(*) as cnt
                    FROM action_items ai JOIN incidents i ON ai.incident_id = i.id
                    WHERE i.venue_id = :vid GROUP BY ai.status"""),
            {"vid": venue_uuid},
        ).fetchall()

    engine.dispose()

    now = datetime.now(timezone.utc)
    incidents_30d = [i for i in incidents if (now - i[3]).days <= 30]
    incidents_60d = [i for i in incidents if (now - i[3]).days <= 60]
    high_severity_30d = [i for i in incidents_30d if i[2] == "High"]

    current_score = scores[0][0] if scores else None
    prev_score = scores[1][0] if len(scores) > 1 else current_score
    score_trend = "declining" if current_score and prev_score and current_score < prev_score else "stable"

    total_actions = sum(r[1] for r in action_stats)
    completed_actions = sum(r[1] for r in action_stats if r[0] == "Complete")

    historical_risk = {
        "total_incidents": len(incidents),
        "incidents_30d": len(incidents_30d),
        "incidents_60d": len(incidents_60d),
        "high_severity_30d": len(high_severity_30d),
        "current_score": current_score,
        "score_trend": score_trend,
        "score_delta": round(current_score - prev_score, 1) if current_score and prev_score else 0,
        "action_completion_rate": round(completed_actions / total_actions * 100, 1) if total_actions > 0 else 0,
        "incident_summary": [
            {"ref_code": i[0], "title": i[1], "severity": i[2], "date": i[3].isoformat()}
            for i in incidents[:5]
        ],
    }

    return {**state, "historical_risk": historical_risk}


async def control_verification_agent(state: UnderwritingState) -> UnderwritingState:
    """Check which corrective actions are completed with verified proof."""
    venue = state.get("venue")
    if not venue:
        return state

    engine = create_engine(SYNC_URL)
    with engine.connect() as conn:
        # Get all actions with their completion status
        actions = conn.execute(
            text("""SELECT ai.title, ai.status, ai.proof_description, ai.completed_at, ai.priority
                    FROM action_items ai JOIN incidents i ON ai.incident_id = i.id
                    WHERE i.venue_id = :vid
                    ORDER BY ai.completed_at DESC NULLS LAST"""),
            {"vid": venue["id"]},
        ).fetchall()

        # Evidence status
        evidence = conn.execute(
            text("""SELECT ei.label, ei.status, ei.kind
                    FROM evidence_items ei JOIN incidents i ON ei.incident_id = i.id
                    WHERE i.venue_id = :vid"""),
            {"vid": venue["id"]},
        ).fetchall()

    engine.dispose()

    verified_controls = [
        {"title": a[0], "proof": a[2], "completed": a[3].isoformat() if a[3] else None}
        for a in actions if a[1] == "Complete"
    ]
    open_controls = [
        {"title": a[0], "priority": a[4], "status": a[1]}
        for a in actions if a[1] != "Complete"
    ]

    total_evidence = len(evidence)
    verified_evidence = len([e for e in evidence if e[1] == "Verified"])
    missing_evidence = [{"label": e[0], "kind": e[2]} for e in evidence if e[1] == "Missing"]

    control_status = {
        "verified_controls": verified_controls,
        "open_controls": open_controls,
        "evidence_completeness_pct": round(verified_evidence / total_evidence * 100, 1) if total_evidence > 0 else 0,
        "missing_evidence": missing_evidence,
        "total_actions": len(actions),
        "completed_actions": len(verified_controls),
    }

    return {**state, "control_status": control_status}


async def guideline_agent(state: UnderwritingState) -> UnderwritingState:
    """RAG: retrieve relevant underwriting/loss-control guidance."""
    venue = state.get("venue")
    historical_risk = state.get("historical_risk")
    if not venue:
        return state

    # Build search queries based on the venue's situation
    queries = [
        "underwriting posture assessment for nightlife venues",
        "loss control requirements for recurring incidents",
    ]
    if historical_risk and historical_risk.get("high_severity_30d", 0) > 0:
        queries.append("high severity incident underwriting conditions")
    if historical_risk and historical_risk.get("score_trend") == "declining":
        queries.append("declining risk score monitoring requirements")

    all_guidelines = []
    for query in queries:
        results_str = RAG_TOOL_FUNCTIONS["search_playbooks"](query=query, top_k=2)
        results = json.loads(results_str)
        for r in results:
            if r["source_id"] not in [g["source_id"] for g in all_guidelines]:
                all_guidelines.append(r)

    return {**state, "guidelines": all_guidelines}


async def draft_agent(state: UnderwritingState) -> UnderwritingState:
    """LLM: compose a structured underwriting posture draft."""
    venue = state.get("venue")
    historical_risk = state.get("historical_risk")
    control_status = state.get("control_status")
    guidelines = state.get("guidelines", [])

    if not venue:
        return state

    context = f"""VENUE:
Name: {venue['name']}
Type: {venue['type']}
Location: {venue['location']}
Capacity: {venue['capacity']}

HISTORICAL RISK:
- Current Score: {historical_risk.get('current_score')}
- Score Trend: {historical_risk.get('score_trend')} ({historical_risk.get('score_delta'):+.1f})
- Incidents (30d): {historical_risk.get('incidents_30d')}
- Incidents (60d): {historical_risk.get('incidents_60d')}
- High severity in 30d: {historical_risk.get('high_severity_30d')}
- Action completion rate: {historical_risk.get('action_completion_rate')}%
- Recent incidents: {json.dumps(historical_risk.get('incident_summary', []), indent=2)}

CONTROL VERIFICATION:
- Evidence completeness: {control_status.get('evidence_completeness_pct')}%
- Verified controls: {json.dumps(control_status.get('verified_controls', []), indent=2)}
- Open controls: {json.dumps(control_status.get('open_controls', []), indent=2)}
- Missing evidence: {json.dumps(control_status.get('missing_evidence', []), indent=2)}

GUIDELINE CITATIONS:
{json.dumps([{"document": g["document"], "section": g["section"], "content": g["content"][:200]} for g in guidelines], indent=2)}
"""

    system_prompt = """You are the Underwriting Draft Agent for Afterlight.

Produce a structured underwriting posture draft as JSON:
{
    "risk_narrative": "2-3 sentence summary of the venue's current risk posture",
    "verified_controls": ["list of controls that are confirmed with proof"],
    "open_gaps": ["list of unresolved issues"],
    "conditions": ["specific conditions to maintain or achieve"],
    "monitoring_requirements": ["ongoing monitoring items"],
    "posture_recommendation": "favorable | conditional | refer | decline_review",
    "posture_rationale": "1-2 sentences explaining the recommendation",
    "citations": [{"source": "document/section", "relevance": "what it supports"}]
}

RULES:
- Base the posture on documented facts only
- If high severity incidents are recent and controls are incomplete, recommend "conditional" or "refer"
- If evidence completeness < 70%, that's a significant gap
- If actions are mostly complete and no recent high severity, "favorable" is appropriate
- You CANNOT make a bind/decline decision — only recommend a posture for human review
- Cite your sources"""

    client = OpenAI(api_key=settings.openai_api_key)
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=2000,
        )
        draft = json.loads(response.choices[0].message.content)
    except Exception as e:
        draft = {"error": str(e), "posture_recommendation": "refer"}

    return {**state, "draft": draft, "posture": draft.get("posture_recommendation", "refer")}


async def guardrail_validator(state: UnderwritingState) -> UnderwritingState:
    """
    Deterministic referral rules — the LLM cannot override these.

    Forced referral if:
    - 2+ high severity incidents in 30 days
    - Evidence completeness below 50%
    - Overdue urgent action items
    """
    historical_risk = state.get("historical_risk", {})
    control_status = state.get("control_status", {})

    referral_reasons = []
    forced_referral = False

    # Rule 1: 2+ high severity in 30 days → forced referral
    if historical_risk.get("high_severity_30d", 0) >= 2:
        referral_reasons.append("Two or more high-severity incidents in the last 30 days")
        forced_referral = True

    # Rule 2: Evidence completeness below 50% → forced referral
    if control_status.get("evidence_completeness_pct", 100) < 50:
        referral_reasons.append(f"Evidence completeness is critically low ({control_status.get('evidence_completeness_pct')}%)")
        forced_referral = True

    # Rule 3: Urgent open actions → forced conditional at minimum
    urgent_open = [c for c in control_status.get("open_controls", []) if c.get("priority") == "Urgent"]
    if len(urgent_open) >= 2:
        referral_reasons.append(f"{len(urgent_open)} urgent corrective actions remain open")
        forced_referral = True

    # Override LLM posture if referral is forced
    posture = state.get("posture", "refer")
    if forced_referral:
        if posture in ("favorable", "conditional"):
            posture = "refer"

    return {
        **state,
        "posture": posture,
        "forced_referral": forced_referral,
        "referral_reasons": referral_reasons,
    }


def build_underwriting_graph() -> StateGraph:
    graph = StateGraph(UnderwritingState)

    graph.add_node("load_venue_data", load_venue_data)
    graph.add_node("historical_risk_agent", historical_risk_agent)
    graph.add_node("control_verification_agent", control_verification_agent)
    graph.add_node("guideline_agent", guideline_agent)
    graph.add_node("draft_agent", draft_agent)
    graph.add_node("guardrail_validator", guardrail_validator)

    graph.set_entry_point("load_venue_data")
    # Parallel: historical risk + control verification
    graph.add_edge("load_venue_data", "historical_risk_agent")
    graph.add_edge("historical_risk_agent", "control_verification_agent")
    graph.add_edge("control_verification_agent", "guideline_agent")
    graph.add_edge("guideline_agent", "draft_agent")
    graph.add_edge("draft_agent", "guardrail_validator")
    graph.add_edge("guardrail_validator", END)

    return graph


underwriting_graph = build_underwriting_graph().compile()


async def run_underwriting_workflow(venue_id: str) -> dict:
    """Execute the underwriting posture workflow for a venue."""
    initial_state: UnderwritingState = {
        "venue_id": venue_id,
        "venue": None,
        "historical_risk": None,
        "control_status": None,
        "guidelines": [],
        "draft": None,
        "posture": None,
        "forced_referral": False,
        "referral_reasons": [],
        "errors": [],
        "_trace": None,
    }

    result = await underwriting_graph.ainvoke(initial_state)
    result.pop("_trace", None)
    return result
