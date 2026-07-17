from decimal import Decimal

import pytest

from foundation.intelligence.ranking.competition import (
    CompetitionDisposition,
    CompetitionOutcome,
    CompetitionReasonCode,
)
from foundation.intelligence.ranking.explanations import build_ranking_explanation


def outcome(disposition=CompetitionDisposition.SELECTED, winner=None):
    reason = (
        CompetitionReasonCode.SELECTED_WITHIN_CAPACITY
        if disposition is CompetitionDisposition.SELECTED
        else CompetitionReasonCode.DUPLICATE_COMPETITION_LOSS
    )
    return CompetitionOutcome("BTC", disposition, reason, Decimal("82.5"), 1, winner)


def test_builds_deterministic_positive_and_limiting_drivers():
    explanation = build_ranking_explanation(
        outcome(),
        {"confidence": 80, "action_strength": 90, "liquidity": 70},
        penalties={"concentration": 12, "freshness": 3},
        max_drivers=2,
    )
    assert [item.factor_name for item in explanation.positive_drivers] == [
        "action_strength", "confidence"
    ]
    assert [item.factor_name for item in explanation.limiting_drivers] == [
        "concentration", "freshness"
    ]


def test_suppression_names_winning_opportunity_and_reason():
    explanation = build_ranking_explanation(
        outcome(CompetitionDisposition.SUPPRESSED, "BTC_PRIMARY"), {"confidence": 80}
    )
    assert "BTC_PRIMARY" in explanation.summary
    assert "DUPLICATE_COMPETITION_LOSS" in explanation.summary


def test_portfolio_context_is_stably_ordered_and_preserved():
    explanation = build_ranking_explanation(
        outcome(),
        {"confidence": 80},
        portfolio_context={"target_gap": 0.2, "concentration_headroom": 0.1},
    )
    assert explanation.portfolio_statement.index("Concentration") < explanation.portfolio_statement.index("Target")
    assert explanation.audit_evidence["portfolio_context"]["target_gap"] == 0.2


def test_audit_evidence_is_immutable():
    explanation = build_ranking_explanation(outcome(), {"confidence": 80})
    with pytest.raises(TypeError):
        explanation.audit_evidence["reason_code"] = "CHANGED"


def test_ties_use_factor_name_and_empty_context_is_explicit():
    explanation = build_ranking_explanation(outcome(), {"zeta": 80, "alpha": 80})
    assert [item.factor_name for item in explanation.positive_drivers] == ["alpha", "zeta"]
    assert explanation.portfolio_statement.startswith("No additional")


def test_rejects_invalid_driver_limit():
    with pytest.raises(ValueError):
        build_ranking_explanation(outcome(), {"confidence": 80}, max_drivers=0)
