"""Tests for the Universal Decision Explanation Engine."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from foundation.intelligence.decision import (
    ActionClassificationResult,
    AllocationResult,
    ConfidenceBand,
    ConfidenceResult,
    ConstraintCheck,
    ConstraintEvaluationResult,
    ConstraintStatus,
    DecisionAction,
    DecisionContext,
    DecisionEvidence,
    DecisionExplanation,
    DecisionInput,
    DecisionScore,
    DecisionValidationError,
    EligibilityCheck,
    EligibilityResult,
    EligibilityStatus,
    ExplanationConfigurationError,
    ExplanationInputError,
    ExplanationProfile,
    UniversalDecisionExplanationEngine,
)


def build_input(
    *,
    asset_id: str = "ETF:VOO",
) -> DecisionInput:
    return DecisionInput(
        asset_id=asset_id,
        asset_class="etf",
        time_horizon="3_year",
        context=DecisionContext(
            portfolio_id="PORTFOLIO-001",
            as_of=datetime.now(timezone.utc),
            portfolio_value=Decimal("100000"),
            available_capital=Decimal("3000"),
            current_position_value=Decimal("5000"),
            current_asset_weight=0.05,
            current_asset_class_weight=0.20,
        ),
        forecast_strength=85.0,
        forecast_confidence=82.0,
        historical_reliability=78.0,
        risk_adjusted_opportunity=80.0,
        market_regime_alignment=72.0,
        diversification_fit=68.0,
        liquidity_quality=95.0,
        valuation_attractiveness=70.0,
        data_quality=90.0,
        evidence=(
            DecisionEvidence(
                evidence_id="EVIDENCE-FORECAST",
                category="forecast",
                source="forecast_engine",
                description="Forecast evidence.",
            ),
            DecisionEvidence(
                evidence_id="EVIDENCE-HISTORY",
                category="validation",
                source="historical_validation",
                description="Historical reliability evidence.",
            ),
        ),
    )


def build_eligibility(
    *,
    asset_id: str = "ETF:VOO",
    status: EligibilityStatus = EligibilityStatus.ELIGIBLE,
) -> EligibilityResult:
    checks = ()

    if status is EligibilityStatus.CONDITIONALLY_ELIGIBLE:
        checks = (
            EligibilityCheck(
                rule_id="minimum_data_quality",
                passed=False,
                message="Data quality is slightly below policy.",
                actual_value=55.0,
                threshold=60.0,
                failure_status=(
                    EligibilityStatus.CONDITIONALLY_ELIGIBLE
                ),
            ),
        )

    return EligibilityResult(
        asset_id=asset_id,
        status=status,
        checks=checks,
        reasons=(
            "Opportunity passes eligibility."
            if status is EligibilityStatus.ELIGIBLE
            else "Data quality is slightly below policy.",
        ),
    )


def build_score() -> DecisionScore:
    return DecisionScore(
        base_score=82.0,
        penalty_score=4.0,
        final_score=78.0,
        component_scores={
            "forecast_strength": 17.0,
            "forecast_confidence": 12.3,
            "historical_reliability": 11.7,
            "liquidity_quality": 4.75,
        },
        penalty_components={
            "data_quality": 2.0,
            "asset_concentration": 2.0,
        },
    )


def build_classification(
    *,
    asset_id: str = "ETF:VOO",
    action: DecisionAction = DecisionAction.BUY,
    eligibility: EligibilityStatus = EligibilityStatus.ELIGIBLE,
) -> ActionClassificationResult:
    return ActionClassificationResult(
        asset_id=asset_id,
        action=action,
        eligibility=eligibility,
        final_score=78.0,
        position_exists=True,
        reasons=("Score classifies the asset as BUY.",),
    )


def build_confidence(
    *,
    asset_id: str = "ETF:VOO",
    value: float = 0.81,
) -> ConfidenceResult:
    return ConfidenceResult(
        asset_id=asset_id,
        raw_confidence=value,
        adjustment_score=0.0,
        final_confidence=value,
        confidence_band=ConfidenceBand.HIGH,
        component_scores={
            "forecast_confidence": 20.5,
            "historical_reliability": 19.5,
        },
        reasons=("Confidence calculated.",),
    )


def build_constraints(
    *,
    asset_id: str = "ETF:VOO",
    status: ConstraintStatus = ConstraintStatus.PASSED,
) -> ConstraintEvaluationResult:
    checks = (
        ConstraintCheck(
            constraint_id="available_capital",
            status=status,
            message=(
                "Available capital is positive."
                if status is ConstraintStatus.PASSED
                else "Available capital requires review."
            ),
            allocation_limit=Decimal("3000"),
        ),
    )

    return ConstraintEvaluationResult(
        asset_id=asset_id,
        status=status,
        checks=checks,
        maximum_permitted_allocation=Decimal("3000"),
        binding_constraint="available_capital",
        reasons=("Constraints evaluated.",),
    )


def build_allocation(
    *,
    asset_id: str = "ETF:VOO",
    action: DecisionAction = DecisionAction.BUY,
    recommended: Decimal = Decimal("1822.50"),
) -> AllocationResult:
    return AllocationResult(
        asset_id=asset_id,
        action=action,
        requested_allocation=Decimal("3000"),
        maximum_allocation=Decimal("3000"),
        recommended_allocation=recommended,
        allocation_percentage=float(recommended / Decimal("3000")),
        binding_constraint="available_capital",
        sizing_factors={
            "action": 0.75,
            "confidence": 0.81,
        },
        reasons=("Allocation calculated.",),
    )


def explain_default() -> DecisionExplanation:
    return UniversalDecisionExplanationEngine().explain(
        build_input(),
        build_eligibility(),
        build_score(),
        build_classification(),
        build_confidence(),
        build_constraints(),
        build_allocation(),
    )


def test_explanation_contains_headline_and_summary() -> None:
    result = explain_default()

    assert "ETF:VOO" in result.headline
    assert "BUY" in result.headline
    assert "78.00" in result.executive_summary
    assert "81.00%" in result.executive_summary


def test_positive_factors_use_structured_components() -> None:
    result = explain_default()

    assert len(result.positive_factors) == 3
    assert any(
        "Forecast Strength" in factor
        for factor in result.positive_factors
    )


def test_negative_factors_include_explicit_penalties() -> None:
    result = explain_default()

    assert any(
        "Data Quality" in factor
        for factor in result.negative_factors
    )
    assert any(
        "Asset Concentration" in factor
        for factor in result.negative_factors
    )


def test_evidence_references_use_evidence_ids() -> None:
    result = explain_default()

    assert result.evidence_references == (
        "EVIDENCE-FORECAST",
        "EVIDENCE-HISTORY",
    )


def test_audit_facts_include_versions_and_values() -> None:
    result = explain_default()

    assert result.audit_facts["asset_id"] == "ETF:VOO"
    assert result.audit_facts["final_score"] == 78.0
    assert result.audit_facts["action"] == "buy"
    assert result.audit_facts["recommended_allocation"] == "1822.50"


def test_conditional_eligibility_creates_warning() -> None:
    result = UniversalDecisionExplanationEngine().explain(
        build_input(),
        build_eligibility(
            status=EligibilityStatus.CONDITIONALLY_ELIGIBLE
        ),
        build_score(),
        build_classification(
            action=DecisionAction.ACCUMULATE,
            eligibility=EligibilityStatus.CONDITIONALLY_ELIGIBLE,
        ),
        build_confidence(),
        build_constraints(status=ConstraintStatus.WARNING),
        build_allocation(
            action=DecisionAction.ACCUMULATE,
            recommended=Decimal("600"),
        ),
    )

    assert any(
        "conditionally eligible" in warning.lower()
        for warning in result.warnings
    )


def test_zero_allocation_creates_warning() -> None:
    result = UniversalDecisionExplanationEngine().explain(
        build_input(),
        build_eligibility(),
        build_score(),
        build_classification(action=DecisionAction.WAIT),
        build_confidence(),
        build_constraints(status=ConstraintStatus.BLOCKED),
        build_allocation(
            action=DecisionAction.WAIT,
            recommended=Decimal("0"),
        ),
    )

    assert any(
        "allocation is zero" in warning.lower()
        for warning in result.warnings
    )


def test_profile_limits_factor_counts() -> None:
    result = UniversalDecisionExplanationEngine().explain(
        build_input(),
        build_eligibility(),
        build_score(),
        build_classification(),
        build_confidence(),
        build_constraints(),
        build_allocation(),
        explanation_profile=ExplanationProfile(
            maximum_positive_factors=1,
            maximum_negative_factors=1,
            maximum_evidence_references=1,
        ),
    )

    assert len(result.positive_factors) == 1
    assert len(result.negative_factors) == 1
    assert len(result.evidence_references) == 1


def test_audit_facts_can_be_disabled() -> None:
    result = UniversalDecisionExplanationEngine().explain(
        build_input(),
        build_eligibility(),
        build_score(),
        build_classification(),
        build_confidence(),
        build_constraints(),
        build_allocation(),
        explanation_profile=ExplanationProfile(
            include_audit_facts=False
        ),
    )

    assert result.audit_facts == {}


def test_asset_identifiers_must_match() -> None:
    with pytest.raises(ExplanationInputError):
        UniversalDecisionExplanationEngine().explain(
            build_input(),
            build_eligibility(asset_id="CRYPTO:BTC"),
            build_score(),
            build_classification(),
            build_confidence(),
            build_constraints(),
            build_allocation(),
        )


def test_actions_must_match() -> None:
    with pytest.raises(ExplanationInputError):
        UniversalDecisionExplanationEngine().explain(
            build_input(),
            build_eligibility(),
            build_score(),
            build_classification(action=DecisionAction.BUY),
            build_confidence(),
            build_constraints(),
            build_allocation(action=DecisionAction.ACCUMULATE),
        )


def test_eligibility_statuses_must_match() -> None:
    with pytest.raises(ExplanationInputError):
        UniversalDecisionExplanationEngine().explain(
            build_input(),
            build_eligibility(
                status=EligibilityStatus.CONDITIONALLY_ELIGIBLE
            ),
            build_score(),
            build_classification(
                eligibility=EligibilityStatus.ELIGIBLE
            ),
            build_confidence(),
            build_constraints(),
            build_allocation(),
        )


def test_invalid_profile_count_is_rejected() -> None:
    with pytest.raises(ExplanationConfigurationError):
        ExplanationProfile(maximum_positive_factors=-1)


def test_explanation_contract_rejects_blank_headline() -> None:
    with pytest.raises(DecisionValidationError):
        DecisionExplanation(
            asset_id="ETF:VOO",
            headline="",
            executive_summary="Summary.",
            eligibility_explanation="Eligible.",
            scoring_explanation="Scored.",
            confidence_explanation="Confidence.",
            constraint_explanation="Constraints.",
            allocation_explanation="Allocation.",
        )
