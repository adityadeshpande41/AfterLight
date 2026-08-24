"""
AI-powered incident extraction from natural language.

Takes free-text description, extracts structured incident fields,
and asks follow-up questions for missing information.
"""

import json

from fastapi import APIRouter
from openai import OpenAI
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/extract", tags=["extract"])


class ExtractionRequest(BaseModel):
    text: str
    follow_up_answers: dict | None = None  # Answers to previous follow-up questions


class ExtractedIncident(BaseModel):
    title: str | None = None
    incident_type: str | None = None
    severity: str | None = None
    location: str | None = None
    time_description: str | None = None
    people: list[str] = []
    summary: str | None = None
    evidence_leads: list[str] = []


class ExtractionResponse(BaseModel):
    extracted: ExtractedIncident
    confidence: float  # 0-1 how confident we are in the extraction
    follow_up_questions: list[str]  # Questions to ask for missing info
    ready_to_confirm: bool  # True if we have enough to create the record


SYSTEM_PROMPT = """You are an incident extraction assistant for Afterlight, a risk-intelligence platform for nightlife venues.

A venue manager is describing an incident in natural language. Extract structured fields from their text.

Extract these fields:
- title: short descriptive title (e.g., "Slip-and-fall near main entrance")
- incident_type: one of [Injury, Security, Property damage, Crowd management]
- severity: one of [Low, Moderate, High] based on:
  - High: EMS called, significant injury, major property damage
  - Moderate: minor injury, security intervention, moderate disruption
  - Low: near-miss, minor issue, no injury
- location: specific location within the venue
- time_description: when it happened (e.g., "around 1am", "during last call")
- people: list of people/roles involved (e.g., ["Security", "EMS", "Manager"])
- summary: clean 1-2 sentence factual summary
- evidence_leads: potential evidence sources mentioned (e.g., ["Camera 3", "door team witnessed"])

Also generate follow-up questions for any critical missing information. Key things to ask about:
- If no time mentioned, ask when
- If severity is unclear, ask about injuries/EMS
- If no witnesses mentioned, ask who saw it
- If no location specifics, ask where exactly

Output JSON:
{
  "extracted": { ...fields above... },
  "confidence": 0.0-1.0,
  "follow_up_questions": ["question 1", ...],
  "ready_to_confirm": true/false
}

Set ready_to_confirm=true if you have at minimum: title, type, severity, location, and summary.
Set confidence based on how much was explicitly stated vs inferred."""


@router.post("", response_model=ExtractionResponse)
async def extract_incident(body: ExtractionRequest):
    """
    Extract structured incident data from natural language text.

    If follow_up_answers are provided, incorporate them into the extraction.
    """
    client = OpenAI(api_key=settings.openai_api_key)

    user_content = f"Incident description:\n{body.text}"
    if body.follow_up_answers:
        user_content += f"\n\nAdditional information provided:\n{json.dumps(body.follow_up_answers)}"

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=1000,
    )

    parsed = json.loads(response.choices[0].message.content)

    return ExtractionResponse(
        extracted=ExtractedIncident(**parsed.get("extracted", {})),
        confidence=parsed.get("confidence", 0.5),
        follow_up_questions=parsed.get("follow_up_questions", []),
        ready_to_confirm=parsed.get("ready_to_confirm", False),
    )
