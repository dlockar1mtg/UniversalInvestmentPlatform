"""Tests for Phase 5.1.1 universal decision contracts."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from foundation.intelligence.decision import (
    DecisionAction,
    DecisionContext,
    DecisionEvidence,
    DecisionInput,
    DecisionPolicy,
    DecisionPolicyError,
    DecisionResult,
    DecisionScore,
    DecisionStatus,
    DecisionValidationError,
    EligibilityStatus,
)


def build_context() -> DecisionContext:
    return DecisionContext(
        portfolio_id="PORTFOLIO-001",
        portfolio_value=Decimal("100000"),
        available_capital=Decimal("3000"),
        current_position_value=Decimal("5000"),
        current_asset_weight=0.05,
        current_asset_class_weight=0.20,
        target_asset_weight=0.10,
        target_asset_class_weight=0.30,
    )


def build_evidence() -> DecisionEvidence:
    return DecisionEvidence(
        evidence_id="EVIDENCE-001",
        category="forecast",
        source="universal_forecasting",
        description="Three-year expected return is positive.",
        value=14.5,
        weight=0.90,
    )


def build_score() -> DecisionScore:
    return DecisionScore(
        base_score=82.0,
        penalty_score=4.0,
        final_score=78.0,
        component_scores={
            "forecast_strength": 85.0,
            "historical_reliability": 76.0,
        },
        penalty_components={
            "concentration": 4.0,
        },
    )


def test_decision_action_values_are_stable() -> None:
    assert DecisionAction.STRONG_BUY.value == "strong_buy"
    assert DecisionAction.INSUFFICIENT_DATA.value == (
        "insufficient_data"
    )


def test_context_accepts_valid_portfolio_state() -> None:
    context = build_context()

    assert context.portfolio_id == "PORTFOLIO-001"
    assert context.available_capital == Decimal("3000")
    assert context.current_asset_weight == 0.05


def test_context_rejects_invalid_weight() -> None:
    with pytest.raises(DecisionValidationError):
        DecisionContext(
            portfolio_id="PORTFOLIO-001",
            current_asset_weight=1.25,
        )


def test_evidence_accepts_traceable_record() -> None:
    evidence = build_evidence()

    assert evidence.source == "universal_forecasting"
    assert evidence.weight == 0.90


def test_evidence_rejects_invalid_weight() -> None:
    with pytest.raises(DecisionValidationError):
        DecisionEvidence(
            evidence_id="EVIDENCE-001",
            category="forecast",
            source="forecasting",
            description="Invalid evidence weight.",
            weight=1.20,
        )


def test_score_accepts_component_breakdown() -> None:
    score = build_score()

    assert score.final_score == 78.0
    assert score.component_scores["forecast_strength"] == 85.0


def test_score_rejects_out_of_range_value() -> None:
    with pytest.raises(DecisionValidationError):
        DecisionScore(
            base_score=101.0,
            penalty_score=0.0,
            final_score=100.0,
        )


def test_decision_input_accepts_universal_scores() -> None:
    decision_input = DecisionInput(
        asset_id="CRYPTO:BTC",
        asset_class="crypto",
        time_horizon="3_year",
        context=build_context(),
        forecast_strength=84.0,
        forecast_confidence=82.0,
        historical_reliability=75.0,
        risk_adjusted_opportunity=70.0,
        market_regime_alignment=68.0,
        diversification_fit=65.0,
        liquidity_quality=95.0,
        valuation_attractiveness=60.0,
        data_quality=92.0,
        evidence=(build_evidence(),),
    )

    assert decision_input.asset_id == "CRYPTO:BTC"
    assert decision_input.data_quality == 92.0
    assert len(decision_input.evidence) == 1


def test_decision_input_rejects_invalid_score() -> None:
    with pytest.raises(DecisionValidationError):
        DecisionInput(
            asset_id="ETF:VOO",
            asset_class="etf",
            time_horizon="1_year",
            context=build_context(),
            forecast_strength=-1.0,
            forecast_confidence=80.0,
            historical_reliability=80.0,
            risk_adjusted_opportunity=80.0,
            market_regime_alignment=80.0,
            diversification_fit=80.0,
            liquidity_quality=80.0,
            valuation_attractiveness=80.0,
            data_quality=80.0,
        )


def test_default_policy_has_ordered_thresholds() -> None:
    policy = DecisionPolicy()

    assert policy.strong_buy_threshold > policy.buy_threshold
    assert policy.buy_threshold > policy.accumulate_threshold
    assert policy.maximum_asset_weight == 0.20


def test_policy_rejects_misordered_thresholds() -> None:
    with pytest.raises(DecisionPolicyError):
        DecisionPolicy(
            strong_buy_threshold=70.0,
            buy_threshold=80.0,
        )


def test_decision_result_accepts_auditable_output() -> None:
    generated_at = datetime.now(timezone.utc)

    result = DecisionResult(
        decision_id="DEC-20260717-BTC-001",
        asset_id="CRYPTO:BTC",
        asset_class="crypto",
        action=DecisionAction.BUY,
        status=DecisionStatus.EVALUATED,
        eligibility=EligibilityStatus.ELIGIBLE,
        score=build_score(),
        confidence=0.84,
        maximum_allocation=Decimal("950"),
        reasons=("Positive forecast.", "Risk budget available."),
        evidence=(build_evidence(),),
        generated_at=generated_at,
        expires_at=generated_at + timedelta(days=1),
    )

    assert result.action is DecisionAction.BUY
    assert result.eligibility is EligibilityStatus.ELIGIBLE
    assert result.maximum_allocation == Decimal("950")


def test_decision_result_rejects_invalid_confidence() -> None:
    with pytest.raises(DecisionValidationError):
        DecisionResult(
            decision_id="DECISION-001",
            asset_id="METAL:GOLD",
            asset_class="metals",
            action=DecisionAction.HOLD,
            status=DecisionStatus.EVALUATED,
            eligibility=EligibilityStatus.ELIGIBLE,
            score=build_score(),
            confidence=1.10,
        )


def test_decision_result_rejects_expired_at_generation() -> None:
    generated_at = datetime.now(timezone.utc)

    with pytest.raises(DecisionValidationError):
        DecisionResult(
            decision_id="DECISION-002",
            asset_id="ETF:SCHD",
            asset_class="etf",
            action=DecisionAction.BUY,
            status=DecisionStatus.EVALUATED,
            eligibility=EligibilityStatus.ELIGIBLE,
            score=build_score(),
            confidence=0.80,
            generated_at=generated_at,
            expires_at=generated_at,
        )


def test_decision_result_rejects_recommendation_above_maximum() -> None:
    with pytest.raises(DecisionValidationError):
        DecisionResult(
            decision_id="DECISION-ALLOCATION-001",
            asset_id="ETF:VOO",
            asset_class="etf",
            action=DecisionAction.BUY,
            status=DecisionStatus.EVALUATED,
            eligibility=EligibilityStatus.ELIGIBLE,
            score=build_score(),
            confidence=0.80,
            maximum_allocation=Decimal("1000"),
            recommended_allocation=Decimal("1001"),
        )
