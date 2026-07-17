"""Tests for the Universal Action Classification Engine."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from foundation.intelligence.decision import (
    ClassificationInputError,
    DecisionAction,
    DecisionContext,
    DecisionEvidence,
    DecisionInput,
    DecisionPolicy,
    DecisionScore,
    EligibilityResult,
    EligibilityStatus,
    UniversalActionClassificationEngine,
)


def build_context(
    *,
    position_value: Decimal = Decimal("0"),
    asset_weight: float = 0.0,
) -> DecisionContext:
    return DecisionContext(
        portfolio_id="PORTFOLIO-001",
        as_of=datetime.now(timezone.utc),
        portfolio_value=Decimal("100000"),
        available_capital=Decimal("3000"),
        current_position_value=position_value,
        current_asset_weight=asset_weight,
        current_asset_class_weight=0.20,
    )


def build_input(
    *,
    position_value: Decimal = Decimal("0"),
    asset_weight: float = 0.0,
) -> DecisionInput:
    return DecisionInput(
        asset_id="ETF:VOO",
        asset_class="etf",
        time_horizon="3_year",
        context=build_context(
            position_value=position_value,
            asset_weight=asset_weight,
        ),
        forecast_strength=80.0,
        forecast_confidence=80.0,
        historical_reliability=80.0,
        risk_adjusted_opportunity=80.0,
        market_regime_alignment=80.0,
        diversification_fit=80.0,
        liquidity_quality=80.0,
        valuation_attractiveness=80.0,
        data_quality=90.0,
        evidence=(
            DecisionEvidence(
                evidence_id="EVIDENCE-001",
                category="forecast",
                source="forecast_engine",
                description="Classification evidence.",
            ),
        ),
    )


def build_score(final_score: float) -> DecisionScore:
    return DecisionScore(
        base_score=final_score,
        penalty_score=0.0,
        final_score=final_score,
    )


def build_eligibility(
    status: EligibilityStatus = EligibilityStatus.ELIGIBLE,
    *,
    asset_id: str = "ETF:VOO",
) -> EligibilityResult:
    return EligibilityResult(
        asset_id=asset_id,
        status=status,
        reasons=(
            "Eligibility condition recorded."
            if status is not EligibilityStatus.ELIGIBLE
            else "Opportunity passes eligibility."
        ,),
    )


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (100.0, DecisionAction.STRONG_BUY),
        (85.0, DecisionAction.STRONG_BUY),
        (84.999, DecisionAction.BUY),
        (72.0, DecisionAction.BUY),
        (71.999, DecisionAction.ACCUMULATE),
        (62.0, DecisionAction.ACCUMULATE),
        (61.999, DecisionAction.WAIT),
        (50.0, DecisionAction.WAIT),
        (49.999, DecisionAction.AVOID),
        (38.0, DecisionAction.AVOID),
        (37.999, DecisionAction.AVOID),
        (25.0, DecisionAction.AVOID),
        (24.999, DecisionAction.AVOID),
        (0.0, DecisionAction.AVOID),
    ],
)
def test_new_opportunity_score_boundaries(
    score: float,
    expected: DecisionAction,
) -> None:
    result = UniversalActionClassificationEngine().classify(
        build_input(),
        build_score(score),
        build_eligibility(),
    )

    assert result.action is expected
    assert result.position_exists is False


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (85.0, DecisionAction.STRONG_BUY),
        (72.0, DecisionAction.BUY),
        (62.0, DecisionAction.ACCUMULATE),
        (50.0, DecisionAction.HOLD),
        (38.0, DecisionAction.REDUCE),
        (25.0, DecisionAction.SELL),
        (0.0, DecisionAction.SELL),
    ],
)
def test_existing_position_score_boundaries(
    score: float,
    expected: DecisionAction,
) -> None:
    result = UniversalActionClassificationEngine().classify(
        build_input(
            position_value=Decimal("5000"),
            asset_weight=0.05,
        ),
        build_score(score),
        build_eligibility(),
    )

    assert result.action is expected
    assert result.position_exists is True


def test_asset_weight_alone_marks_position_as_existing() -> None:
    result = UniversalActionClassificationEngine().classify(
        build_input(
            position_value=Decimal("0"),
            asset_weight=0.01,
        ),
        build_score(55.0),
        build_eligibility(),
    )

    assert result.action is DecisionAction.HOLD
    assert result.position_exists is True


def test_ineligible_status_overrides_high_score() -> None:
    result = UniversalActionClassificationEngine().classify(
        build_input(),
        build_score(99.0),
        build_eligibility(EligibilityStatus.INELIGIBLE),
    )

    assert result.action is DecisionAction.INELIGIBLE


def test_insufficient_data_overrides_high_score() -> None:
    result = UniversalActionClassificationEngine().classify(
        build_input(),
        build_score(99.0),
        build_eligibility(
            EligibilityStatus.INSUFFICIENT_DATA
        ),
    )

    assert result.action is DecisionAction.INSUFFICIENT_DATA


def test_conditional_high_score_is_capped_at_accumulate() -> None:
    result = UniversalActionClassificationEngine().classify(
        build_input(),
        build_score(92.0),
        build_eligibility(
            EligibilityStatus.CONDITIONALLY_ELIGIBLE
        ),
    )

    assert result.action is DecisionAction.ACCUMULATE
    assert any(
        "caps positive actions" in reason
        for reason in result.reasons
    )


def test_conditional_buy_score_is_capped_at_accumulate() -> None:
    result = UniversalActionClassificationEngine().classify(
        build_input(),
        build_score(78.0),
        build_eligibility(
            EligibilityStatus.CONDITIONALLY_ELIGIBLE
        ),
    )

    assert result.action is DecisionAction.ACCUMULATE


def test_conditional_accumulate_remains_accumulate() -> None:
    result = UniversalActionClassificationEngine().classify(
        build_input(),
        build_score(66.0),
        build_eligibility(
            EligibilityStatus.CONDITIONALLY_ELIGIBLE
        ),
    )

    assert result.action is DecisionAction.ACCUMULATE


def test_conditional_hold_remains_hold_for_existing_position() -> None:
    result = UniversalActionClassificationEngine().classify(
        build_input(
            position_value=Decimal("1000"),
            asset_weight=0.01,
        ),
        build_score(55.0),
        build_eligibility(
            EligibilityStatus.CONDITIONALLY_ELIGIBLE
        ),
    )

    assert result.action is DecisionAction.HOLD


def test_custom_policy_thresholds_are_used() -> None:
    policy = DecisionPolicy(
        strong_buy_threshold=90.0,
        buy_threshold=80.0,
        accumulate_threshold=70.0,
        hold_threshold=60.0,
        reduce_threshold=40.0,
        sell_threshold=20.0,
    )

    result = UniversalActionClassificationEngine().classify(
        build_input(),
        build_score(75.0),
        build_eligibility(),
        policy,
    )

    assert result.action is DecisionAction.ACCUMULATE


def test_result_contains_score_reason() -> None:
    result = UniversalActionClassificationEngine().classify(
        build_input(),
        build_score(74.0),
        build_eligibility(),
    )

    assert result.final_score == 74.0
    assert any(
        "74.00" in reason
        for reason in result.reasons
    )


def test_eligibility_asset_must_match_input() -> None:
    with pytest.raises(ClassificationInputError):
        UniversalActionClassificationEngine().classify(
            build_input(),
            build_score(80.0),
            build_eligibility(asset_id="CRYPTO:BTC"),
        )
