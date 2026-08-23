"""
Mitigation Agent — drafts a structured action plan using LLM.

Uses:
- Confirmed incident facts
- Evidence findings (from Evidence Agent)
- Pattern analysis (from Pattern Agent)
- Playbook citations (from Playbook Agent — RAG)
- Validation feedback (if retrying)

Outputs a structured, citation-backed action plan draft.
Cannot make binding decisions.
"""

import json

from openai import OpenAI
from pydantic import BaseModel

from app.config import settings


class ActionPlanItem(BaseModel):
    """A single proposed corrective action."""

    title: str
    owner: str
    priority: str  # Urgent, Important, Routine
    due_description: str
    required_proof: str
    citation: str  # Source: evidence finding, pattern, or playbook


class ActionPlanDraft(BaseModel):
    """Structured output from the Mitigation Agent."""

    actions: list[ActionPlanItem]
    reasoning: str


SYSTEM_PROMPT = """You are the Mitigation Agent for Afterlight, an operational risk-intelligence platform for nightlife venues.

Your job: Given confirmed incident facts, evidence findings, pattern analysis, and approved playbook citations, draft a structured corrective action plan.

CRITICAL RULES:
- Only propose actions supported by confirmed facts OR approved playbook guidance
- Each action MUST cite its source — either an evidence finding, pattern, or playbook section
- Playbook citations are your primary guidance — they represent approved response patterns
- You CANNOT make binding decisions — this is a DRAFT for human review
- Actions must be specific, measurable, and assignable
- Priority must be exactly one of: Urgent, Important, Routine
- Owner must be a role: "Venue Manager", "Security Lead", "Facilities", "Door Team Lead", "Bar Manager"
- Keep to 3-5 actions maximum
- If playbook guidance exists for the situation, your actions should align with it

Output a JSON object:
{
  "actions": [
    {
      "title": "clear action description",
      "owner": "role name",
      "priority": "Urgent|Important|Routine",
      "due_description": "specific timeframe (e.g., Within 24 hours)",
      "required_proof": "what evidence proves this action was completed",
      "citation": "Source: [document/section] or [finding reference]"
    }
  ],
  "reasoning": "brief explanation of how these actions address identified risks, citing playbook guidance"
}"""


async def mitigation_agent(state: dict) -> dict:
    """
    Draft a structured action plan grounded in findings and playbook citations.
    """
    incident = state.get("incident")
    evidence_assessment = state.get("evidence_assessment")
    pattern_analysis = state.get("pattern_analysis")
    findings = state.get("findings", [])
    playbook_citations = state.get("playbook_citations", [])
    validation_feedback = state.get("validation_feedback")

    if not incident:
        return {**state, "action_plan_draft": []}

    # Build context for the LLM
    context_parts = [
        f"""INCIDENT:
- ID: {incident['ref_code']}
- Title: {incident['title']}
- Type: {incident['type']}
- Severity: {incident['severity']}
- Location: {incident['location']}
- Time: {incident['occurred_at']}
- Summary: {incident['summary']}
- Responders: {', '.join(incident.get('people', []))}""",

        f"""EVIDENCE ASSESSMENT:
- Completeness: {evidence_assessment.get('completeness_pct', 0)}%
- Verified items: {evidence_assessment.get('verified_count', 0)} / {evidence_assessment.get('total_required', 0)}
- Missing items: {', '.join(evidence_assessment.get('missing_items', []))}
- Has urgent gaps: {evidence_assessment.get('has_urgent_gaps', False)}""" if evidence_assessment else "",

        f"""FINDINGS:
{json.dumps(findings, indent=2)}""",

        f"""PATTERN ANALYSIS:
- Pattern detected: {pattern_analysis.get('pattern_detected', False)}
- Incidents in 60 days: {pattern_analysis.get('incidents_60d', 0)}
- Trend: {pattern_analysis.get('trend', 'unknown')}
- Top location: {pattern_analysis.get('top_location', 'unknown')}
- Night cluster: {pattern_analysis.get('night_cluster_count', 0)} incidents between midnight and 2 AM
- Summary: {pattern_analysis.get('summary', '')}
- Supporting incidents: {', '.join(pattern_analysis.get('supporting_incident_ids', []))}""" if pattern_analysis else "",
    ]

    # Add playbook citations — this is the RAG grounding
    if playbook_citations:
        citation_text = "\n\nAPPROVED PLAYBOOK GUIDANCE (use these to ground your recommendations):\n"
        for i, cite in enumerate(playbook_citations, 1):
            citation_text += f"\n[Playbook {i}] {cite['document']} / {cite['section']} (relevance: {cite['relevance_score']}):\n"
            citation_text += f"{cite['content']}\n"
        context_parts.append(citation_text)
    else:
        context_parts.append("\nNo playbook citations available for this incident type.")

    # Add validation feedback if this is a retry
    if validation_feedback:
        context_parts.append(f"\n\nVALIDATION FEEDBACK (fix these issues):\n{validation_feedback}")

    context = "\n\n".join(part for part in context_parts if part)

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=2000,
        )

        raw_output = response.choices[0].message.content
        parsed = json.loads(raw_output)

        # Validate with Pydantic
        plan = ActionPlanDraft.model_validate(parsed)

        return {
            **state,
            "action_plan_draft": [a.model_dump() for a in plan.actions],
        }

    except Exception as e:
        return {
            **state,
            "action_plan_draft": [],
            "errors": state.get("errors", []) + [f"Mitigation agent error: {str(e)}"],
            "needs_human_review": True,
        }
