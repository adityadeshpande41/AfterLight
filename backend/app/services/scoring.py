"""
Deterministic Savings Score calculator.

The score is NEVER calculated by an LLM. It uses a versioned formula
with factor-level explanations and source IDs.

Formula:
    RiskIndex = min(100,
        baseline_exposure
        + incident_severity_and_recency
        + evidence_gap
        + open_action_gap
        + repeat_pattern_risk
        - verified_control_credit
    )
    SavingsScore = max(0, 100 - RiskIndex)
"""

from dataclasses import dataclass
from datetime import datetime, timezone


FORMULA_VERSION = "1.0.0"


@dataclass
class ScoreFactors:
    """Individual risk factors that compose the score."""

    baseline_exposure: float
    incident_severity_and_recency: float
    evidence_gap: float
    open_action_gap: float
    repeat_pattern_risk: float
    verified_control_credit: float

    @property
    def risk_index(self) -> float:
        raw = (
            self.baseline_exposure
            + self.incident_severity_and_recency
            + self.evidence_gap
            + self.open_action_gap
            + self.repeat_pattern_risk
            - self.verified_control_credit
        )
        return min(100.0, max(0.0, raw))

    @property
    def savings_score(self) -> float:
        return max(0.0, 100.0 - self.risk_index)

    def to_dict(self) -> dict:
        return {
            "formula_version": FORMULA_VERSION,
            "baseline_exposure": self.baseline_exposure,
            "incident_severity_and_recency": self.incident_severity_and_recency,
            "evidence_gap": self.evidence_gap,
            "open_action_gap": self.open_action_gap,
            "repeat_pattern_risk": self.repeat_pattern_risk,
            "verified_control_credit": self.verified_control_credit,
            "risk_index": self.risk_index,
            "savings_score": self.savings_score,
        }


@dataclass
class VenueRiskInput:
    """Input data needed to calculate a venue's score."""

    capacity: int
    # Incidents in the scoring window (last 90 days)
    incidents: list["IncidentInput"]
    # Evidence completeness across active incidents (0-100)
    evidence_completeness_pct: float
    # Fraction of actions that are still open (0.0 - 1.0)
    open_action_ratio: float
    # Number of verified controls (completed actions with proof)
    verified_controls: int
    # Whether a repeat pattern is detected
    repeat_pattern_detected: bool


@dataclass
class IncidentInput:
    """Minimal incident info for scoring."""

    severity: str  # "Low", "Moderate", "High"
    occurred_at: datetime


def _severity_weight(severity: str) -> float:
    return {"High": 10.0, "Moderate": 5.0, "Low": 2.0}.get(severity, 3.0)


def _recency_multiplier(occurred_at: datetime, now: datetime) -> float:
    """More recent incidents weigh heavier. Decays over 90 days."""
    days_ago = (now - occurred_at).days
    if days_ago <= 7:
        return 1.3
    elif days_ago <= 30:
        return 1.1
    elif days_ago <= 60:
        return 0.9
    else:
        return 0.6


def calculate_score(input: VenueRiskInput, now: datetime | None = None) -> ScoreFactors:
    """
    Calculate the deterministic Savings Score for a venue.

    Returns ScoreFactors with the full breakdown.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # 1. Baseline exposure — larger venues have more inherent risk
    if input.capacity >= 800:
        baseline_exposure = 12.0
    elif input.capacity >= 500:
        baseline_exposure = 8.0
    elif input.capacity >= 200:
        baseline_exposure = 5.0
    else:
        baseline_exposure = 3.0

    # 2. Incident severity and recency
    incident_severity_and_recency = 0.0
    for incident in input.incidents:
        weight = _severity_weight(incident.severity)
        multiplier = _recency_multiplier(incident.occurred_at, now)
        incident_severity_and_recency += weight * multiplier

    # 3. Evidence gap — how much evidence is missing
    evidence_gap = (100.0 - input.evidence_completeness_pct) * 0.25

    # 4. Open action gap — unresolved corrective actions
    open_action_gap = input.open_action_ratio * 20.0

    # 5. Repeat pattern risk — bonus penalty for detected patterns
    repeat_pattern_risk = 10.0 if input.repeat_pattern_detected else 0.0

    # 6. Verified control credit — reward for completed controls with proof
    verified_control_credit = min(input.verified_controls * 4.0, 20.0)

    return ScoreFactors(
        baseline_exposure=baseline_exposure,
        incident_severity_and_recency=round(incident_severity_and_recency, 2),
        evidence_gap=round(evidence_gap, 2),
        open_action_gap=round(open_action_gap, 2),
        repeat_pattern_risk=repeat_pattern_risk,
        verified_control_credit=round(verified_control_credit, 2),
    )
