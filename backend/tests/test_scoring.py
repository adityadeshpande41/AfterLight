"""Tests for the deterministic scoring service."""

from datetime import datetime, timezone

from app.services.scoring import IncidentInput, ScoreFactors, VenueRiskInput, calculate_score


def test_score_is_bounded_0_to_100():
    """SavingsScore must always be between 0 and 100."""
    # Worst case: huge venue, many severe recent incidents, no evidence, all actions open
    worst = VenueRiskInput(
        capacity=1200,
        incidents=[
            IncidentInput(severity="High", occurred_at=datetime(2026, 8, 22, tzinfo=timezone.utc)),
            IncidentInput(severity="High", occurred_at=datetime(2026, 8, 21, tzinfo=timezone.utc)),
            IncidentInput(severity="High", occurred_at=datetime(2026, 8, 20, tzinfo=timezone.utc)),
        ],
        evidence_completeness_pct=0.0,
        open_action_ratio=1.0,
        verified_controls=0,
        repeat_pattern_detected=True,
    )
    result = calculate_score(worst, now=datetime(2026, 8, 23, tzinfo=timezone.utc))
    assert 0.0 <= result.savings_score <= 100.0
    assert 0.0 <= result.risk_index <= 100.0

    # Best case: small venue, no incidents, perfect evidence, all actions closed
    best = VenueRiskInput(
        capacity=100,
        incidents=[],
        evidence_completeness_pct=100.0,
        open_action_ratio=0.0,
        verified_controls=5,
        repeat_pattern_detected=False,
    )
    result = calculate_score(best, now=datetime(2026, 8, 23, tzinfo=timezone.utc))
    assert 0.0 <= result.savings_score <= 100.0
    assert 0.0 <= result.risk_index <= 100.0


def test_score_is_deterministic():
    """Same inputs must always produce the same score."""
    input_data = VenueRiskInput(
        capacity=650,
        incidents=[
            IncidentInput(severity="High", occurred_at=datetime(2026, 8, 23, 1, 20, tzinfo=timezone.utc)),
            IncidentInput(severity="Moderate", occurred_at=datetime(2026, 8, 9, tzinfo=timezone.utc)),
        ],
        evidence_completeness_pct=67.0,
        open_action_ratio=0.75,
        verified_controls=1,
        repeat_pattern_detected=True,
    )
    now = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)

    result_a = calculate_score(input_data, now=now)
    result_b = calculate_score(input_data, now=now)

    assert result_a.savings_score == result_b.savings_score
    assert result_a.risk_index == result_b.risk_index
    assert result_a.to_dict() == result_b.to_dict()


def test_moonlight_club_scenario():
    """The Moonlight Club demo should produce a score around 58."""
    input_data = VenueRiskInput(
        capacity=650,
        incidents=[
            IncidentInput(severity="High", occurred_at=datetime(2026, 8, 23, 1, 20, tzinfo=timezone.utc)),
            IncidentInput(severity="Moderate", occurred_at=datetime(2026, 8, 9, 0, 44, tzinfo=timezone.utc)),
            IncidentInput(severity="Moderate", occurred_at=datetime(2026, 7, 28, 1, 56, tzinfo=timezone.utc)),
        ],
        evidence_completeness_pct=67.0,
        open_action_ratio=0.75,  # 3 of 4 actions not complete
        verified_controls=1,  # 1 completed action with proof
        repeat_pattern_detected=True,
    )
    now = datetime(2026, 8, 24, 2, 0, tzinfo=timezone.utc)
    result = calculate_score(input_data, now=now)

    # Moonlight is a high-attention venue: low score, elevated risk index
    assert result.savings_score < 55
    assert result.risk_index > 45


def test_healthy_venue():
    """A healthy venue with no issues should score high."""
    input_data = VenueRiskInput(
        capacity=900,
        incidents=[],
        evidence_completeness_pct=95.0,
        open_action_ratio=0.0,
        verified_controls=5,
        repeat_pattern_detected=False,
    )
    result = calculate_score(input_data, now=datetime(2026, 8, 23, tzinfo=timezone.utc))

    assert result.savings_score >= 75
    assert result.risk_index <= 25


def test_no_incidents_still_has_baseline():
    """Even without incidents, baseline exposure exists."""
    input_data = VenueRiskInput(
        capacity=650,
        incidents=[],
        evidence_completeness_pct=100.0,
        open_action_ratio=0.0,
        verified_controls=0,
        repeat_pattern_detected=False,
    )
    result = calculate_score(input_data)

    # Baseline for 650-cap venue is 8
    assert result.baseline_exposure == 8.0
    assert result.risk_index == 8.0
    assert result.savings_score == 92.0


def test_factors_dict_includes_version():
    """The factor breakdown must include the formula version."""
    input_data = VenueRiskInput(
        capacity=300,
        incidents=[],
        evidence_completeness_pct=100.0,
        open_action_ratio=0.0,
        verified_controls=0,
        repeat_pattern_detected=False,
    )
    result = calculate_score(input_data)
    d = result.to_dict()

    assert "formula_version" in d
    assert d["formula_version"] == "1.0.0"
    assert "risk_index" in d
    assert "savings_score" in d
