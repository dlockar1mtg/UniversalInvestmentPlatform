"""Tests for the Universal Eligibility and Data Quality Engine."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from foundation.intelligence.decision import (
    DecisionContext,
    DecisionEvidence,
    DecisionInput,
    DecisionPolicy,
    EligibilityStatus,
    UniversalEligibilityEngine,
)


def build_context(
    *,
    available_capital: Decimal = Decimal("3000"),
    asset_weight: float = 0.05,
    asset_class_weight: float = 0.20,
) -> DecisionContext:
    return DecisionContext(
        portfolio_id="PORTFOLIO-001",
        as_of=datetime.now(timezone.utc),
        portfolio_value=Decimal("100000"),
        available_capital=available_capital,
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
        description="Forecast evidence.",
        value=75.0,
        observed_at=datetime.now(timezone.utc) - timedelta(days=age_days),
    )


def build_input(
    *,
    data_quality: float = 85.0,
    forecast_confidence: float = 80.0,
    historical_reliability: float = 75.0,
    liquidity_quality: float = 90.0,
    context: DecisionContext | None = None,
    evidence: tuple[DecisionEvidence, ...] | None = None,
) -> DecisionInput:
    return DecisionInput(
        asset_id="CRYPTO:BTC",
        asset_class="crypto",
        time_horizon="3_year",
        context=context or build_context(),
        forecast_strength=82.0,
        forecast_confidence=forecast_confidence,
        historical_reliability=historical_reliability,
        risk_adjusted_opportunity=74.0,
        market_regime_alignment=68.0,
        diversification_fit=65.0,
        liquidity_quality=liquidity_quality,
        valuation_attractiveness=62.0,
        data_quality=data_quality,
        evidence=evidence
        if evidence is not None
        else (build_evidence(),),
    )


def test_fully_qualified_opportunity_is_eligible() -> None:
    result = UniversalEligibilityEngine().evaluate(build_input())

    assert result.status is EligibilityStatus.ELIGIBLE
    assert result.may_proceed_to_scoring is True
    assert len(result.failed_checks) == 0


def test_small_data_quality_shortfall_is_conditional() -> None:
    result = UniversalEligibilityEngine().evaluate(
        build_input(data_quality=55.0)
    )

    assert result.status is EligibilityStatus.CONDITIONALLY_ELIGIBLE
    assert result.may_proceed_to_scoring is True


def test_large_data_quality_shortfall_is_insufficient() -> None:
    result = UniversalEligibilityEngine().evaluate(
        build_input(data_quality=40.0)
    )

    assert result.status is EligibilityStatus.INSUFFICIENT_DATA
    assert result.may_proceed_to_scoring is False


def test_low_forecast_confidence_is_insufficient() -> None:
    result = UniversalEligibilityEngine().evaluate(
        build_input(forecast_confidence=30.0)
    )

    assert result.status is EligibilityStatus.INSUFFICIENT_DATA


def test_small_reliability_shortfall_is_conditional() -> None:
    result = UniversalEligibilityEngine().evaluate(
        build_input(historical_reliability=45.0)
    )

    assert result.status is EligibilityStatus.CONDITIONALLY_ELIGIBLE


def test_materially_low_liquidity_is_ineligible() -> None:
    result = UniversalEligibilityEngine().evaluate(
        build_input(liquidity_quality=20.0)
    )

    assert result.status is EligibilityStatus.INELIGIBLE
    assert result.may_proceed_to_scoring is False


def test_missing_evidence_is_insufficient() -> None:
    result = UniversalEligibilityEngine().evaluate(
        build_input(evidence=())
    )

    assert result.status is EligibilityStatus.INSUFFICIENT_DATA


def test_all_stale_evidence_is_insufficient() -> None:
    result = UniversalEligibilityEngine().evaluate(
        build_input(evidence=(build_evidence(age_days=90),))
    )

    assert result.status is EligibilityStatus.INSUFFICIENT_DATA


def test_partially_stale_evidence_is_conditional() -> None:
    result = UniversalEligibilityEngine().evaluate(
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

    assert result.status is EligibilityStatus.CONDITIONALLY_ELIGIBLE


def test_negative_capital_is_ineligible_by_default() -> None:
    result = UniversalEligibilityEngine().evaluate(
        build_input(
            context=build_context(
                available_capital=Decimal("-100"),
            )
        )
    )

    assert result.status is EligibilityStatus.INELIGIBLE


def test_policy_can_allow_negative_capital() -> None:
    result = UniversalEligibilityEngine().evaluate(
        build_input(
            context=build_context(
                available_capital=Decimal("-100"),
            )
        ),
        DecisionPolicy(allow_negative_available_capital=True),
    )

    assert result.status is EligibilityStatus.ELIGIBLE


def test_excess_asset_weight_is_ineligible() -> None:
    result = UniversalEligibilityEngine().evaluate(
        build_input(
            context=build_context(asset_weight=0.25)
        )
    )

    assert result.status is EligibilityStatus.INELIGIBLE


def test_excess_asset_class_weight_is_ineligible() -> None:
    result = UniversalEligibilityEngine().evaluate(
        build_input(
            context=build_context(asset_class_weight=0.60)
        )
    )

    assert result.status is EligibilityStatus.INELIGIBLE


def test_ineligible_status_takes_precedence_over_missing_data() -> None:
    result = UniversalEligibilityEngine().evaluate(
        build_input(
            data_quality=20.0,
            liquidity_quality=10.0,
            evidence=(),
        )
    )

    assert result.status is EligibilityStatus.INELIGIBLE


def test_custom_policy_thresholds_are_applied() -> None:
    result = UniversalEligibilityEngine().evaluate(
        build_input(data_quality=85.0),
        DecisionPolicy(
            minimum_data_quality=90.0,
            conditional_shortfall_tolerance=10.0,
        ),
    )

    assert result.status is EligibilityStatus.CONDITIONALLY_ELIGIBLE


def test_invalid_policy_evidence_count_is_rejected() -> None:
    with pytest.raises(ValueError):
        DecisionPolicy(minimum_evidence_count=-1)
