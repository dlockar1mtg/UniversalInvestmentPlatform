"""Tests for the Universal Decision Scoring Engine."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from foundation.intelligence.decision import (
    DecisionContext,
    DecisionEvidence,
    DecisionInput,
    DecisionPolicy,
    DecisionScoringError,
    DecisionScoringProfile,
    EligibilityResult,
    EligibilityStatus,
    IneligibleScoringError,
    ScoringConfigurationError,
    UniversalDecisionScoringEngine,
    UniversalEligibilityEngine,
)


def build_context(
    *,
    asset_weight: float = 0.05,
    asset_class_weight: float = 0.20,
) -> DecisionContext:
    return DecisionContext(
        portfolio_id="PORTFOLIO-001",
        as_of=datetime.now(timezone.utc),
        portfolio_value=Decimal("100000"),
        available_capital=Decimal("3000"),
        current_position_value=Decimal("5000"),
        current_asset_weight=asset_weight,
        current_asset_class_weight=asset_class_weight,
    )


def build_evidence(
    *,
    evidence_id: str = "EVIDENCE-001",
    age_days: int = 0,
) -> DecisionEvidence:
    return DecisionEvidence(
        evidence_id=evidence_id,
        category="forecast",
        source="forecast_engine",
        description="Scoring evidence.",
        value=80.0,
        observed_at=(
            datetime.now(timezone.utc)
            - timedelta(days=age_days)
        ),
    )


def build_input(
    *,
    context: DecisionContext | None = None,
    data_quality: float = 100.0,
    metadata: dict | None = None,
    forecast_strength: float = 80.0,
    forecast_confidence: float = 80.0,
    historical_reliability: float = 80.0,
    risk_adjusted_opportunity: float = 80.0,
    market_regime_alignment: float = 80.0,
    diversification_fit: float = 80.0,
    liquidity_quality: float = 80.0,
    valuation_attractiveness: float = 80.0,
    evidence: tuple[DecisionEvidence, ...] | None = None,
) -> DecisionInput:
    return DecisionInput(
        asset_id="CRYPTO:BTC",
        asset_class="crypto",
        time_horizon="3_year",
        context=context or build_context(),
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
            evidence if evidence is not None else (build_evidence(),)
        ),
        metadata=metadata or {},
    )


def test_equal_components_produce_expected_base_score() -> None:
    score = UniversalDecisionScoringEngine().score(build_input())

    assert score.base_score == pytest.approx(80.0)
    assert score.penalty_score == pytest.approx(0.0)
    assert score.final_score == pytest.approx(80.0)


def test_weighted_components_are_auditable() -> None:
    score = UniversalDecisionScoringEngine().score(build_input())

    assert score.component_scores["forecast_strength"] == 16.0
    assert score.component_scores["forecast_confidence"] == 12.0
    assert score.component_scores["liquidity_quality"] == 4.0
    assert sum(score.component_scores.values()) == pytest.approx(
        score.base_score
    )


def test_component_weighting_uses_all_input_values() -> None:
    score = UniversalDecisionScoringEngine().score(
        build_input(
            forecast_strength=100.0,
            forecast_confidence=0.0,
            historical_reliability=0.0,
            risk_adjusted_opportunity=0.0,
            market_regime_alignment=0.0,
            diversification_fit=0.0,
            liquidity_quality=0.0,
            valuation_attractiveness=0.0,
        ),
        decision_policy=DecisionPolicy(
            minimum_forecast_confidence=0.0,
            minimum_historical_reliability=0.0,
            minimum_liquidity_quality=0.0,
        ),
    )

    assert score.base_score == pytest.approx(20.0)


def test_data_quality_creates_explicit_penalty() -> None:
    score = UniversalDecisionScoringEngine().score(
        build_input(data_quality=75.0)
    )

    assert score.penalty_components["data_quality"] == pytest.approx(
        2.0
    )
    assert score.final_score == pytest.approx(
        score.base_score - 2.0
    )


def test_conditional_eligibility_creates_penalty() -> None:
    decision_input = build_input(data_quality=55.0)

    score = UniversalDecisionScoringEngine().score(decision_input)

    assert score.penalty_components[
        "conditional_eligibility"
    ] == pytest.approx(4.0)


def test_asset_concentration_penalty_begins_above_warning_ratio() -> None:
    score = UniversalDecisionScoringEngine().score(
        build_input(
            context=build_context(asset_weight=0.175)
        )
    )

    assert score.penalty_components[
        "asset_concentration"
    ] == pytest.approx(3.0)


def test_no_asset_penalty_below_warning_ratio() -> None:
    score = UniversalDecisionScoringEngine().score(
        build_input(
            context=build_context(asset_weight=0.15)
        )
    )

    assert "asset_concentration" not in score.penalty_components


def test_asset_class_concentration_penalty_is_applied() -> None:
    score = UniversalDecisionScoringEngine().score(
        build_input(
            context=build_context(asset_class_weight=0.4375)
        )
    )

    assert score.penalty_components[
        "asset_class_concentration"
    ] == pytest.approx(3.0)


def test_partial_stale_evidence_creates_penalties() -> None:
    score = UniversalDecisionScoringEngine().score(
        build_input(
            evidence=(
                build_evidence(
                    evidence_id="FRESH",
                    age_days=5,
                ),
                build_evidence(
                    evidence_id="STALE",
                    age_days=90,
                ),
            )
        )
    )

    assert score.penalty_components[
        "conditional_eligibility"
    ] == pytest.approx(4.0)
    assert score.penalty_components[
        "partial_evidence_freshness"
    ] == pytest.approx(3.0)


def test_evidence_conflict_score_creates_scaled_penalty() -> None:
    score = UniversalDecisionScoringEngine().score(
        build_input(
            metadata={"evidence_conflict_score": 50.0}
        )
    )

    assert score.penalty_components[
        "evidence_conflict"
    ] == pytest.approx(4.0)


def test_invalid_evidence_conflict_score_is_rejected() -> None:
    with pytest.raises(DecisionScoringError):
        UniversalDecisionScoringEngine().score(
            build_input(
                metadata={"evidence_conflict_score": "high"}
            )
        )


def test_out_of_range_evidence_conflict_score_is_rejected() -> None:
    with pytest.raises(DecisionScoringError):
        UniversalDecisionScoringEngine().score(
            build_input(
                metadata={"evidence_conflict_score": 125.0}
            )
        )


def test_ineligible_asset_cannot_be_scored() -> None:
    with pytest.raises(IneligibleScoringError):
        UniversalDecisionScoringEngine().score(
            build_input(liquidity_quality=20.0)
        )


def test_insufficient_data_asset_cannot_be_scored() -> None:
    with pytest.raises(IneligibleScoringError):
        UniversalDecisionScoringEngine().score(
            build_input(data_quality=20.0)
        )


def test_external_eligibility_asset_must_match_input() -> None:
    eligibility = EligibilityResult(
        asset_id="ETF:VOO",
        status=EligibilityStatus.ELIGIBLE,
    )

    with pytest.raises(DecisionScoringError):
        UniversalDecisionScoringEngine().score(
            build_input(),
            eligibility_result=eligibility,
        )


def test_external_eligible_result_can_be_used() -> None:
    decision_input = build_input()
    eligibility = UniversalEligibilityEngine().evaluate(
        decision_input
    )

    score = UniversalDecisionScoringEngine().score(
        decision_input,
        eligibility_result=eligibility,
    )

    assert score.final_score == pytest.approx(80.0)


def test_custom_scoring_weights_are_applied() -> None:
    weights = {
        "forecast_strength": 1.0,
        "forecast_confidence": 0.0,
        "historical_reliability": 0.0,
        "risk_adjusted_opportunity": 0.0,
        "market_regime_alignment": 0.0,
        "diversification_fit": 0.0,
        "liquidity_quality": 0.0,
        "valuation_attractiveness": 0.0,
    }

    score = UniversalDecisionScoringEngine().score(
        build_input(forecast_strength=92.0),
        scoring_profile=DecisionScoringProfile(
            component_weights=weights
        ),
    )

    assert score.base_score == pytest.approx(92.0)


def test_weights_must_sum_to_one() -> None:
    invalid_weights = {
        "forecast_strength": 0.20,
        "forecast_confidence": 0.15,
        "historical_reliability": 0.15,
        "risk_adjusted_opportunity": 0.15,
        "market_regime_alignment": 0.10,
        "diversification_fit": 0.10,
        "liquidity_quality": 0.05,
        "valuation_attractiveness": 0.05,
    }

    with pytest.raises(ScoringConfigurationError):
        DecisionScoringProfile(
            component_weights=invalid_weights
        )


def test_missing_weight_component_is_rejected() -> None:
    invalid_weights = {
        "forecast_strength": 0.25,
        "forecast_confidence": 0.15,
        "historical_reliability": 0.15,
        "risk_adjusted_opportunity": 0.15,
        "market_regime_alignment": 0.10,
        "diversification_fit": 0.10,
        "liquidity_quality": 0.10,
    }

    with pytest.raises(ScoringConfigurationError):
        DecisionScoringProfile(
            component_weights=invalid_weights
        )


def test_final_score_cannot_fall_below_zero() -> None:
    profile = DecisionScoringProfile(
        maximum_data_quality_penalty=100.0,
        conditional_eligibility_penalty=100.0,
    )

    score = UniversalDecisionScoringEngine().score(
        build_input(data_quality=50.0),
        scoring_profile=profile,
    )

    assert score.final_score == 0.0
