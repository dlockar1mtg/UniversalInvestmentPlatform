"""Tests for the Universal Decision Orchestrator."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from foundation.intelligence.decision import (
    AllocationProfile,
    DecisionAction,
    DecisionContext,
    DecisionEvidence,
    DecisionInput,
    DecisionStatus,
    EligibilityStatus,
    OrchestrationConfigurationError,
    OrchestrationInputError,
    OrchestrationProfile,
    UniversalDecisionOrchestrator,
)


FIXED_TIME = datetime(
    2026,
    7,
    17,
    20,
    0,
    0,
    tzinfo=timezone.utc,
)


def build_input(
    *,
    asset_id: str = "ETF:VOO",
    forecast_strength: float = 85.0,
    forecast_confidence: float = 85.0,
    historical_reliability: float = 80.0,
    risk_adjusted_opportunity: float = 82.0,
    market_regime_alignment: float = 75.0,
    diversification_fit: float = 80.0,
    liquidity_quality: float = 95.0,
    valuation_attractiveness: float = 78.0,
    data_quality: float = 95.0,
    available_capital: Decimal = Decimal("3000"),
    position_value: Decimal = Decimal("0"),
    asset_weight: float = 0.0,
    class_weight: float = 0.20,
    evidence: tuple[DecisionEvidence, ...] | None = None,
    metadata: dict | None = None,
) -> DecisionInput:
    return DecisionInput(
        asset_id=asset_id,
        asset_class="etf",
        time_horizon="3_year",
        context=DecisionContext(
            portfolio_id="PORTFOLIO-001",
            as_of=FIXED_TIME,
            portfolio_value=Decimal("100000"),
            available_capital=available_capital,
            current_position_value=position_value,
            current_asset_weight=asset_weight,
            current_asset_class_weight=class_weight,
        ),
        forecast_strength=forecast_strength,
        forecast_confidence=forecast_confidence,
        historical_reliability=historical_reliability,
        risk_adjusted_opportunity=risk_adjusted_opportunity,
        market_regime_alignment=market_regime_alignment,
        diversification_fit=diversification_fit,
        liquidity_quality=liquidity_quality,
        valuation_attractiveness=valuation_attractiveness,
        data_quality=data_quality,
        evidence=(
            evidence
            if evidence is not None
            else (
                DecisionEvidence(
                    evidence_id="EVIDENCE-001",
                    category="forecast",
                    source="forecast_engine",
                    description="Orchestrator evidence.",
                    observed_at=FIXED_TIME,
                ),
            )
        ),
        metadata=metadata or {},
    )


def test_orchestrator_produces_complete_decision() -> None:
    result = UniversalDecisionOrchestrator().evaluate(
        build_input(),
        generated_at=FIXED_TIME,
    )

    decision = result.decision_result

    assert decision.status is DecisionStatus.EVALUATED
    assert decision.eligibility is EligibilityStatus.ELIGIBLE
    assert decision.action in {
        DecisionAction.BUY,
        DecisionAction.STRONG_BUY,
    }
    assert decision.confidence > 0
    assert decision.maximum_allocation == Decimal("3000.00")
    assert decision.recommended_allocation > Decimal("0")
    assert result.explanation.headline
    assert result.engine_version == "5.1.8"


def test_ineligible_opportunity_short_circuits_scoring() -> None:
    result = UniversalDecisionOrchestrator().evaluate(
        build_input(liquidity_quality=10.0),
        generated_at=FIXED_TIME,
    )

    assert result.eligibility_result.status is EligibilityStatus.INELIGIBLE
    assert result.decision_result.action is DecisionAction.INELIGIBLE
    assert result.decision_result.score.final_score == 0.0
    assert (
        result.decision_result.score.scoring_version
        == "5.1.8-short-circuit"
    )
    assert result.decision_result.recommended_allocation == Decimal("0")


def test_insufficient_data_short_circuits_scoring() -> None:
    result = UniversalDecisionOrchestrator().evaluate(
        build_input(data_quality=20.0),
        generated_at=FIXED_TIME,
    )

    assert (
        result.eligibility_result.status
        is EligibilityStatus.INSUFFICIENT_DATA
    )
    assert (
        result.decision_result.action
        is DecisionAction.INSUFFICIENT_DATA
    )
    assert result.decision_result.recommended_allocation == Decimal("0")


def test_requested_allocation_is_respected() -> None:
    result = UniversalDecisionOrchestrator().evaluate(
        build_input(),
        requested_allocation=Decimal("1000"),
        generated_at=FIXED_TIME,
    )

    assert result.allocation_result.requested_allocation == Decimal("1000")
    assert result.decision_result.recommended_allocation <= Decimal("1000")


def test_zero_available_capital_produces_zero_allocation() -> None:
    result = UniversalDecisionOrchestrator().evaluate(
        build_input(available_capital=Decimal("0")),
        generated_at=FIXED_TIME,
    )

    assert result.decision_result.recommended_allocation == Decimal("0")
    assert result.constraint_result.may_allocate is False


def test_custom_allocation_profile_is_applied() -> None:
    result = UniversalDecisionOrchestrator().evaluate(
        build_input(),
        allocation_profile=AllocationProfile(
            maximum_single_decision_fraction=0.25
        ),
        generated_at=FIXED_TIME,
    )

    assert (
        result.allocation_result.sizing_factors[
            "single_decision_limit"
        ]
        == 0.25
    )


def test_decision_identifier_is_reproducible() -> None:
    orchestrator = UniversalDecisionOrchestrator()
    decision_input = build_input()

    first = orchestrator.evaluate(
        decision_input,
        generated_at=FIXED_TIME,
    )
    second = orchestrator.evaluate(
        decision_input,
        generated_at=FIXED_TIME,
    )

    assert first.decision_id == second.decision_id


def test_decision_identifier_changes_with_time() -> None:
    orchestrator = UniversalDecisionOrchestrator()
    decision_input = build_input()

    first = orchestrator.evaluate(
        decision_input,
        generated_at=FIXED_TIME,
    )
    second = orchestrator.evaluate(
        decision_input,
        generated_at=FIXED_TIME.replace(minute=1),
    )

    assert first.decision_id != second.decision_id


def test_expiration_is_calculated_from_profile() -> None:
    result = UniversalDecisionOrchestrator().evaluate(
        build_input(),
        generated_at=FIXED_TIME,
        orchestration_profile=OrchestrationProfile(
            expiration_hours=48
        ),
    )

    assert (
        result.decision_result.expires_at
        - result.decision_result.generated_at
    ).total_seconds() == 48 * 60 * 60


def test_explicit_decision_id_is_preserved() -> None:
    result = UniversalDecisionOrchestrator().evaluate(
        build_input(),
        generated_at=FIXED_TIME,
        decision_id="DECISION-CUSTOM-001",
    )

    assert result.decision_id == "DECISION-CUSTOM-001"


def test_blank_decision_id_is_rejected() -> None:
    with pytest.raises(OrchestrationInputError):
        UniversalDecisionOrchestrator().evaluate(
            build_input(),
            generated_at=FIXED_TIME,
            decision_id=" ",
        )


def test_naive_generation_timestamp_is_rejected() -> None:
    with pytest.raises(OrchestrationInputError):
        UniversalDecisionOrchestrator().evaluate(
            build_input(),
            generated_at=datetime(2026, 7, 17, 20, 0, 0),
        )


def test_component_versions_are_preserved() -> None:
    result = UniversalDecisionOrchestrator().evaluate(
        build_input(),
        generated_at=FIXED_TIME,
    )

    versions = result.decision_result.metadata["component_versions"]

    assert versions["scoring"]
    assert versions["classification"] == "5.1.4"
    assert versions["confidence"] == "5.1.5"
    assert versions["allocation"] == "5.1.6"
    assert versions["explanation"] == "5.1.7"


def test_explanation_is_attached_to_metadata() -> None:
    result = UniversalDecisionOrchestrator().evaluate(
        build_input(),
        generated_at=FIXED_TIME,
    )

    explanation = result.decision_result.metadata["explanation"]

    assert explanation["headline"] == result.explanation.headline
    assert explanation["executive_summary"]


def test_policy_violations_are_collected() -> None:
    result = UniversalDecisionOrchestrator().evaluate(
        build_input(liquidity_quality=10.0),
        generated_at=FIXED_TIME,
    )

    assert result.decision_result.policy_violations


def test_invalid_expiration_hours_are_rejected() -> None:
    with pytest.raises(OrchestrationConfigurationError):
        OrchestrationProfile(expiration_hours=0)
