"""
Input guardrails for the Risk Copilot.

Checks:
1. Off-topic detection — is this about venue operations/risk?
2. Safety — prompt injection, jailbreak attempts
3. Scope — questions the copilot can't answer (legal, medical, pricing)
4. Length/quality — too short, too long, gibberish
"""

import re
from dataclasses import dataclass


@dataclass
class GuardrailResult:
    blocked: bool
    reason: str | None = None
    response: str | None = None


# Patterns that indicate off-topic questions
OFF_TOPIC_PATTERNS = [
    r"\b(recipe|cook|weather|sports|movie|music|game|homework)\b",
    r"\b(stock|crypto|bitcoin|invest|trading)\b",
    r"\b(dating|relationship|love|breakup)\b",
    r"\b(write me a poem|tell me a joke|sing|story)\b",
    r"\b(politics|election|president|congress)\b",
]

# Patterns indicating prompt injection / jailbreak
INJECTION_PATTERNS = [
    r"ignore (previous|all|your) (instructions|rules|prompts)",
    r"you are now",
    r"pretend (to be|you are)",
    r"forget (everything|your rules|your instructions)",
    r"system prompt",
    r"reveal your",
    r"DAN mode",
    r"jailbreak",
    r"\[INST\]",
    r"<\|im_start\|>",
]

# Topics the copilot explicitly cannot advise on
OUT_OF_SCOPE_PATTERNS = [
    r"\b(sue|lawsuit|lawyer|attorney|legal action|liability)\b",
    r"\b(diagnosis|medical advice|treatment|prescription)\b",
    r"\b(insurance (price|quote|premium|rate|cost))\b",
    r"\b(fire|terminate|dismiss) (them|him|her|the employee)\b",
    r"\b(coverage decision|bind|decline|underwrite)\b",
]

OFF_TOPIC_RESPONSE = (
    "I'm the Afterlight Risk Copilot — I help with your venue's operational risk data: "
    "incidents, evidence, scores, actions, and safety patterns. "
    "I can't help with topics outside that scope. "
    "Try asking something like: 'What evidence is missing from INC-1042?' or 'Why did my score change?'"
)

INJECTION_RESPONSE = (
    "I can't process that request. I'm here to help with your venue's "
    "operational risk data. What would you like to know about your incidents, "
    "evidence, or score?"
)

SCOPE_RESPONSES = {
    "legal": (
        "I can show you what the documented record contains, but I can't provide "
        "legal advice or make liability determinations. For legal questions, please "
        "consult a qualified attorney. Would you like me to summarize the incident facts instead?"
    ),
    "medical": (
        "I can tell you what was documented about an incident response, but I can't "
        "provide medical advice. For medical questions, please consult a healthcare professional."
    ),
    "insurance": (
        "I can show you your risk factors and documented readiness, but pricing and "
        "coverage decisions are made by your underwriter through a separate human-reviewed process. "
        "I can help you understand what affects your Savings Score."
    ),
    "employment": (
        "I can help you understand incident patterns and operational data, but I can't "
        "advise on employment decisions. That's a conversation for HR and legal counsel."
    ),
    "underwriting": (
        "Underwriting decisions (bind, decline, coverage terms) are made by human underwriters "
        "through a separate reviewed process. I can help you understand your documented risk "
        "factors and what actions improve your posture."
    ),
}


def check_guardrails(message: str) -> GuardrailResult:
    """Run all input guardrails. Returns blocked=True if the message should not proceed."""

    # 0. Basic quality check
    if len(message.strip()) < 3:
        return GuardrailResult(
            blocked=True,
            reason="too_short",
            response="Could you say a bit more? I need enough context to look up relevant information.",
        )
    if len(message) > 2000:
        return GuardrailResult(
            blocked=True,
            reason="too_long",
            response="That's quite long — could you break it into a shorter, focused question?",
        )

    message_lower = message.lower()

    # 1. Prompt injection / jailbreak detection
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, message_lower):
            return GuardrailResult(
                blocked=True,
                reason="injection_attempt",
                response=INJECTION_RESPONSE,
            )

    # 2. Out-of-scope topics (before off-topic, since these are more specific)
    for pattern in OUT_OF_SCOPE_PATTERNS:
        match = re.search(pattern, message_lower)
        if match:
            matched_text = match.group(0)
            if any(word in matched_text for word in ["sue", "lawsuit", "lawyer", "attorney", "legal", "liability"]):
                return GuardrailResult(blocked=True, reason="legal_advice", response=SCOPE_RESPONSES["legal"])
            if any(word in matched_text for word in ["diagnosis", "medical", "treatment", "prescription"]):
                return GuardrailResult(blocked=True, reason="medical_advice", response=SCOPE_RESPONSES["medical"])
            if any(word in matched_text for word in ["price", "quote", "premium", "rate", "cost"]):
                return GuardrailResult(blocked=True, reason="insurance_pricing", response=SCOPE_RESPONSES["insurance"])
            if any(word in matched_text for word in ["fire", "terminate", "dismiss"]):
                return GuardrailResult(blocked=True, reason="employment_advice", response=SCOPE_RESPONSES["employment"])
            if any(word in matched_text for word in ["bind", "decline", "underwrite", "coverage decision"]):
                return GuardrailResult(blocked=True, reason="underwriting_decision", response=SCOPE_RESPONSES["underwriting"])

    # 3. Off-topic detection
    for pattern in OFF_TOPIC_PATTERNS:
        if re.search(pattern, message_lower):
            return GuardrailResult(
                blocked=True,
                reason="off_topic",
                response=OFF_TOPIC_RESPONSE,
            )

    # Passed all guardrails
    return GuardrailResult(blocked=False)
