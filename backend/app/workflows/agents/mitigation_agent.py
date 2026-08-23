"""
Mitigation Agent — drafts a structured action plan using LLM.

Uses confirmed facts + evidence findings + pattern findings to create
a citation-backed action plan draft. Cannot make binding decisions.
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
    due_description: str  # e.g. "Within 24 hours", "Within 7 days"
    required_proof: str
    citation: str  # What evidence/finding supports this action


class ActionPlanDraft(BaseModel):
    """Structured output from the Mitigation Agent."""

    actions: list[ActionPlanItem]
    reasoning: str


SYSTEM_PROMPT = """You are the Mitigation Agent for Afterlight, an operational risk-intelligence platform for nightlife venues.

Your job: Given confirmed incident facts, evidence findings, and pattern analysis, draft a structured corrective action plan.

Rules:
- Only propose actions supported by the confirmed facts
- Each action must cite its source (evidence finding, pattern, or incident detail)
- You cannot make binding decisions — this is a DRAFT for human review
- Actions should be specific, measurable, and assignable
- Priority must be one of: Urgent, Important, Routine
- Owner should be a role (e.g., "Venue Manager", "Security Lead", "Facilities")
- Keep to 3-5 actions maximum

Output a JSON object matching this schema:
{
  "actions": [
    {
      "title": "action description",
      "owner": "role",
      "priority": "Urgent|Important|Routine",
      "due_description": "timeframe",
      "required_proof": "what evidence proves this was done",
      "citation": "source fact or finding"
    }
  ],
  "reasoning": "brief explanation of why these actions address the identified risks"
}"""


async def mitigation_agent(state: dict) -> dict:
    """
    Draft a structured action plan based on findings.

    Uses OpenAI with strict schema output.
    """
    incident = state.get("incident")
    evidence_assessment = state.get("evidence_assessment")
    pattern_analysis = state.get("pattern_analysis")
    findings = state.get("findings", [])

    if not incident:
        return {**state, "action_plan_draft": []}

    # Build context for the LLM
    context = f"""INCIDENT:
- ID: {incident['ref_code']}
- Title: {incident['title']}
- Type: {incident['type']}
- Severity: {incident['severity']}
- Location: {incident['location']}
- Time: {incident['occurred_at']}
- Summary: {incident['summary']}
- Responders: {', '.join(incident.get('people', []))}

EVIDENCE ASSESSMENT:
- Completeness: {evidence_assessment.get('completeness_pct', 0)}%
- Missing items: {', '.join(evidence_assessment.get('missing_items', []))}
- Urgent gaps: {evidence_assessment.get('has_urgent_gaps', False)}

FINDINGS:
{json.dumps(findings, indent=2)}

PATTERN ANALYSIS:
{json.dumps(pattern_analysis, indent=2) if pattern_analysis else 'No pattern data available'}
"""

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
            max_tokens=1500,
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
        # If LLM fails, return empty draft and flag for human review
        return {
            **state,
            "action_plan_draft": [],
            "errors": state.get("errors", []) + [f"Mitigation agent error: {str(e)}"],
            "needs_human_review": True,
        }
