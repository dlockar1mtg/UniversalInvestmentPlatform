"""Tests for the Universal Confidence Aggregation Engine."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from foundation.intelligence.decision import (
    ConfidenceBand,
    ConfidenceConfigurationError,
    ConfidenceInputError,
    ConfidenceProfile,
    ConfidenceResult,
    DecisionContext,
    DecisionEvidence,
    DecisionInput,
    DecisionPolicy,
    DecisionValidationError,
    EligibilityResult,
    EligibilityStatus,
    UniversalConfidenceAggregationEngine,
    UniversalEligibilityEngine,
)


def build_context() -> DecisionContext:
    return DecisionContext(
        portfolio_id="PORTFOLIO-001",
        as_of=datetime.now(timezone.utc),
        portfolio_value=Decimal("100000"),
        available_capital=Decimal("3000"),
        current_position_value=Decimal("5000"),
        current_asset_weight=0.05,
        current_asset_class_weight=0.20,
    )


def build_evidence(
    *,
    evidence_id: str = "EVIDENCE-001",
    weight: float = 1.0,
    age_days: int = 0,
) -> DecisionEvidence:
    return DecisionEvidence(
        evidence_id=evidence_id,
        category="forecast",
        source="forecast_engine",
        description="Confidence evidence.",
        weight=weight,
        observed_at=(
            datetime.now(timezone.utc)
            - timedelta(days=age_days)
        ),
    )


def build_input(
    *,
    forecast_confidence: float = 80.0,
    historical_reliability: float = 80.0,
    data_quality: float = 80.0,
    evidence: tuple[DecisionEvidence, ...] | None = None,
    metadata: dict | None = None,
) -> DecisionInput:
    return DecisionInput(
        asset_id="CRYPTO:BTC",
        asset_class="crypto",
        time_horizon="3_year",
        context=build_context(),
        forecast_strength=80.0,
        forecast_confidence=forecast_confidence,
        historical_reliability=historical_reliability,
        risk_adjusted_opportunity=80.0,
        market_regime_alignment=80.0,
        diversification_fit=80.0,
        liquidity_quality=80.0,
        valuation_attractiveness=80.0,
        data_quality=data_quality,
        evidence=(
            evidence
            if evidence is not None
            else (build_evidence(weight=0.80),)
        ),
        metadata=metadata or {},
    )


def eligible_result(
    decision_input: DecisionInput,
) -> EligibilityResult:
    return UniversalEligibilityEngine().evaluate(decision_input)


def test_default_components_produce_expected_raw_confidence() -> None:
    decision_input = build_input()

    result = UniversalConfidenceAggregationEngine().aggregate(
        decision_input,
        eligible_result(decision_input),
    )

    assert result.raw_confidence == pytest.approx(0.83)
    assert result.final_confidence == pytest.approx(0.83)
    assert result.confidence_band is ConfidenceBand.HIGH


def test_component_scores_are_auditable() -> None:
    decision_input = build_input()

    result = UniversalConfidenceAggregationEngine().aggregate(
        decision_input,
        eligible_result(decision_input),
    )

    assert result.component_scores["forecast_confidence"] == 20.0
    assert result.component_scores["historical_reliability"] == 20.0
    assert result.component_scores["data_quality"] == 16.0
    assert sum(result.component_scores.values()) == pytest.approx(83.0)


@pytest.mark.parametrize(
    ("confidence", "expected_band"),
    [
        (0.90, ConfidenceBand.VERY_HIGH),
        (0.75, ConfidenceBand.HIGH),
        (0.60, ConfidenceBand.MODERATE),
        (0.45, ConfidenceBand.LOW),
        (0.20, ConfidenceBand.VERY_LOW),
    ],
)
def test_confidence_band_boundaries(
    confidence: float,
    expected_band: ConfidenceBand,
) -> None:
    profile = ConfidenceProfile()

    band = UniversalConfidenceAggregationEngine._classify_band(
        confidence=confidence,
        profile=profile,
    )

    assert band is expected_band


def test_conditional_eligibility_reduces_confidence() -> None:
    decision_input = build_input(data_quality=55.0)
    eligibility = eligible_result(decision_input)

    result = UniversalConfidenceAggregationEngine().aggregate(
        decision_input,
        eligibility,
    )

    assert eligibility.status is EligibilityStatus.CONDITIONALLY_ELIGIBLE
    assert result.adjustments["conditional_eligibility"] == 5.0
    assert result.final_confidence < result.raw_confidence


def test_partial_stale_evidence_reduces_confidence() -> None:
    decision_input = build_input(
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
    eligibility = eligible_result(decision_input)

    result = UniversalConfidenceAggregationEngine().aggregate(
        decision_input,
        eligibility,
    )

    assert result.adjustments["partial_evidence_freshness"] == 5.0


def test_limited_evidence_adjustment_is_applied() -> None:
    decision_input = build_input(evidence=())
    policy = DecisionPolicy(minimum_evidence_count=2)
    eligibility = UniversalEligibilityEngine().evaluate(
        decision_input,
        policy,
    )

    result = UniversalConfidenceAggregationEngine().aggregate(
        decision_input,
        eligibility,
        decision_policy=policy,
    )

    assert result.adjustments["limited_evidence"] == 10.0


def test_model_disagreement_creates_scaled_adjustment() -> None:
    decision_input = build_input(
        metadata={"forecast_model_disagreement": 50.0}
    )

    result = UniversalConfidenceAggregationEngine().aggregate(
        decision_input,
        eligible_result(decision_input),
    )

    assert result.adjustments["model_disagreement"] == 5.0


def test_unsupported_assumptions_create_adjustment() -> None:
    decision_input = build_input(
        metadata={"unsupported_assumption_score": 50.0}
    )

    result = UniversalConfidenceAggregationEngine().aggregate(
        decision_input,
        eligible_result(decision_input),
    )

    assert result.adjustments["unsupported_assumptions"] == 4.0


def test_regime_instability_creates_adjustment() -> None:
    decision_input = build_input(
        metadata={"regime_instability_score": 100.0}
    )

    result = UniversalConfidenceAggregationEngine().aggregate(
        decision_input,
        eligible_result(decision_input),
    )

    assert result.adjustments["regime_instability"] == 7.0


def test_evidence_conflict_reduces_consistency_component() -> None:
    decision_input = build_input(
        metadata={"evidence_conflict_score": 60.0}
    )

    result = UniversalConfidenceAggregationEngine().aggregate(
        decision_input,
        eligible_result(decision_input),
    )

    assert result.component_scores["evidence_consistency"] == 4.0


def test_evidence_quality_uses_average_evidence_weight() -> None:
    decision_input = build_input(
        evidence=(
            build_evidence(evidence_id="A", weight=1.0),
            build_evidence(evidence_id="B", weight=0.50),
        )
    )

    result = UniversalConfidenceAggregationEngine().aggregate(
        decision_input,
        eligible_result(decision_input),
    )

    assert result.component_scores["evidence_quality"] == pytest.approx(
        11.25
    )


def test_invalid_metadata_score_is_rejected() -> None:
    decision_input = build_input(
        metadata={"forecast_model_disagreement": "high"}
    )

    with pytest.raises(ConfidenceInputError):
        UniversalConfidenceAggregationEngine().aggregate(
            decision_input,
            eligible_result(decision_input),
        )


def test_out_of_range_metadata_score_is_rejected() -> None:
    decision_input = build_input(
        metadata={"regime_instability_score": 125.0}
    )

    with pytest.raises(ConfidenceInputError):
        UniversalConfidenceAggregationEngine().aggregate(
            decision_input,
            eligible_result(decision_input),
        )


def test_eligibility_asset_must_match_input() -> None:
    decision_input = build_input()
    eligibility = EligibilityResult(
        asset_id="ETF:VOO",
        status=EligibilityStatus.ELIGIBLE,
        reasons=("Eligible.",),
    )

    with pytest.raises(ConfidenceInputError):
        UniversalConfidenceAggregationEngine().aggregate(
            decision_input,
            eligibility,
        )


def test_custom_weights_are_applied() -> None:
    weights = {
        "forecast_confidence": 1.0,
        "historical_reliability": 0.0,
        "data_quality": 0.0,
        "evidence_quality": 0.0,
        "evidence_consistency": 0.0,
        "eligibility_quality": 0.0,
    }

    decision_input = build_input(forecast_confidence=91.0)

    result = UniversalConfidenceAggregationEngine().aggregate(
        decision_input,
        eligible_result(decision_input),
        confidence_profile=ConfidenceProfile(
            component_weights=weights
        ),
    )

    assert result.raw_confidence == pytest.approx(0.91)


def test_weights_must_sum_to_one() -> None:
    invalid_weights = {
        "forecast_confidence": 0.20,
        "historical_reliability": 0.20,
        "data_quality": 0.20,
        "evidence_quality": 0.15,
        "evidence_consistency": 0.10,
        "eligibility_quality": 0.05,
    }

    with pytest.raises(ConfidenceConfigurationError):
        ConfidenceProfile(component_weights=invalid_weights)


def test_missing_weight_component_is_rejected() -> None:
    invalid_weights = {
        "forecast_confidence": 0.25,
        "historical_reliability": 0.25,
        "data_quality": 0.20,
        "evidence_quality": 0.15,
        "evidence_consistency": 0.15,
    }

    with pytest.raises(ConfidenceConfigurationError):
        ConfidenceProfile(component_weights=invalid_weights)


def test_thresholds_must_be_ordered() -> None:
    with pytest.raises(ConfidenceConfigurationError):
        ConfidenceProfile(
            very_high_threshold=0.70,
            high_threshold=0.85,
        )


def test_final_confidence_cannot_fall_below_zero() -> None:
    profile = ConfidenceProfile(
        maximum_limited_evidence_adjustment=100.0,
        maximum_model_disagreement_adjustment=100.0,
    )
    policy = DecisionPolicy(minimum_evidence_count=1)

    decision_input = build_input(
        evidence=(),
        metadata={"forecast_model_disagreement": 100.0},
    )
    eligibility = UniversalEligibilityEngine().evaluate(
        decision_input,
        policy,
    )

    result = UniversalConfidenceAggregationEngine().aggregate(
        decision_input,
        eligibility,
        decision_policy=policy,
        confidence_profile=profile,
    )

    assert result.final_confidence == 0.0


def test_confidence_result_rejects_invalid_raw_confidence() -> None:
    with pytest.raises(DecisionValidationError):
        ConfidenceResult(
            asset_id="ETF:VOO",
            raw_confidence=1.10,
            adjustment_score=0.0,
            final_confidence=1.0,
            confidence_band=ConfidenceBand.VERY_HIGH,
            reasons=("Invalid raw confidence.",),
        )


def test_confidence_result_requires_reasons() -> None:
    with pytest.raises(DecisionValidationError):
        ConfidenceResult(
            asset_id="ETF:VOO",
            raw_confidence=0.80,
            adjustment_score=0.0,
            final_confidence=0.80,
            confidence_band=ConfidenceBand.HIGH,
        )


