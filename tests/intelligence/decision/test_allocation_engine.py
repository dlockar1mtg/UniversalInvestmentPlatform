"""Tests for the Universal Allocation Engine."""

from decimal import Decimal

import pytest

from foundation.intelligence.decision import (
    ActionClassificationResult,
    AllocationConfigurationError,
    AllocationInputError,
    AllocationProfile,
    ConfidenceBand,
    ConfidenceResult,
    ConstraintEvaluationResult,
    ConstraintStatus,
    DecisionAction,
    EligibilityStatus,
    UniversalAllocationEngine,
)


def build_classification(
    action: DecisionAction = DecisionAction.BUY,
    *,
    eligibility: EligibilityStatus = EligibilityStatus.ELIGIBLE,
    asset_id: str = "ETF:VOO",
) -> ActionClassificationResult:
    return ActionClassificationResult(
        asset_id=asset_id,
        action=action,
        eligibility=eligibility,
        final_score=80.0,
        position_exists=False,
        reasons=("Classified.",),
    )


def build_confidence(
    value: float = 0.80,
    *,
    asset_id: str = "ETF:VOO",
) -> ConfidenceResult:
    return ConfidenceResult(
        asset_id=asset_id,
        raw_confidence=value,
        adjustment_score=0.0,
        final_confidence=value,
        confidence_band=ConfidenceBand.HIGH,
        reasons=("Confidence calculated.",),
    )


def build_constraints(
    maximum: Decimal = Decimal("3000"),
    *,
    status: ConstraintStatus = ConstraintStatus.PASSED,
    binding: str | None = "available_capital",
    asset_id: str = "ETF:VOO",
) -> ConstraintEvaluationResult:
    return ConstraintEvaluationResult(
        asset_id=asset_id,
        status=status,
        maximum_permitted_allocation=maximum,
        binding_constraint=binding,
        reasons=("Constraints evaluated.",),
    )


def test_buy_allocation_uses_action_and_confidence() -> None:
    result = UniversalAllocationEngine().recommend(
        build_classification(DecisionAction.BUY),
        build_confidence(0.80),
        build_constraints(),
    )

    assert result.recommended_allocation == Decimal("1800.00")
    assert result.sizing_factors["action"] == 0.75
    assert result.sizing_factors["confidence"] == 0.80


def test_strong_buy_can_use_full_confidence_adjusted_amount() -> None:
    result = UniversalAllocationEngine().recommend(
        build_classification(DecisionAction.STRONG_BUY),
        build_confidence(0.90),
        build_constraints(),
    )

    assert result.recommended_allocation == Decimal("2700.00")


def test_accumulate_uses_smaller_action_factor() -> None:
    result = UniversalAllocationEngine().recommend(
        build_classification(DecisionAction.ACCUMULATE),
        build_confidence(0.80),
        build_constraints(),
    )

    assert result.recommended_allocation == Decimal("1200.00")


@pytest.mark.parametrize(
    "action",
    [
        DecisionAction.HOLD,
        DecisionAction.WAIT,
        DecisionAction.REDUCE,
        DecisionAction.SELL,
        DecisionAction.AVOID,
        DecisionAction.INELIGIBLE,
        DecisionAction.INSUFFICIENT_DATA,
    ],
)
def test_non_increasing_actions_receive_zero(
    action: DecisionAction,
) -> None:
    result = UniversalAllocationEngine().recommend(
        build_classification(action),
        build_confidence(),
        build_constraints(),
    )

    assert result.recommended_allocation == Decimal("0")


def test_blocked_constraints_receive_zero() -> None:
    result = UniversalAllocationEngine().recommend(
        build_classification(),
        build_confidence(),
        build_constraints(
            maximum=Decimal("0"),
            status=ConstraintStatus.BLOCKED,
        ),
    )

    assert result.recommended_allocation == Decimal("0")


def test_requested_allocation_caps_the_sizing_base() -> None:
    result = UniversalAllocationEngine().recommend(
        build_classification(DecisionAction.BUY),
        build_confidence(0.80),
        build_constraints(),
        requested_allocation=Decimal("1000"),
    )

    assert result.requested_allocation == Decimal("1000")
    assert result.recommended_allocation == Decimal("600.00")


def test_requested_allocation_cannot_exceed_maximum() -> None:
    result = UniversalAllocationEngine().recommend(
        build_classification(DecisionAction.STRONG_BUY),
        build_confidence(1.0),
        build_constraints(maximum=Decimal("1000")),
        requested_allocation=Decimal("5000"),
    )

    assert result.requested_allocation == Decimal("1000")
    assert result.recommended_allocation == Decimal("1000.00")


def test_conditional_eligibility_reduces_allocation() -> None:
    result = UniversalAllocationEngine().recommend(
        build_classification(
            DecisionAction.ACCUMULATE,
            eligibility=EligibilityStatus.CONDITIONALLY_ELIGIBLE,
        ),
        build_confidence(0.80),
        build_constraints(),
    )

    assert result.sizing_factors["eligibility"] == 0.50
    assert result.recommended_allocation == Decimal("600.00")


def test_minimum_confidence_multiplier_is_applied() -> None:
    result = UniversalAllocationEngine().recommend(
        build_classification(DecisionAction.BUY),
        build_confidence(0.10),
        build_constraints(),
    )

    assert result.sizing_factors["confidence"] == 0.25
    assert result.recommended_allocation == Decimal("562.50")


def test_custom_profile_changes_sizing() -> None:
    profile = AllocationProfile(
        buy_multiplier=1.0,
        minimum_confidence_multiplier=0.0,
        maximum_single_decision_fraction=0.50,
    )

    result = UniversalAllocationEngine().recommend(
        build_classification(DecisionAction.BUY),
        build_confidence(0.80),
        build_constraints(),
        allocation_profile=profile,
    )

    assert result.recommended_allocation == Decimal("1200.00")


def test_rounding_increment_is_respected() -> None:
    profile = AllocationProfile(
        rounding_increment=Decimal("10")
    )

    result = UniversalAllocationEngine().recommend(
        build_classification(DecisionAction.BUY),
        build_confidence(0.83),
        build_constraints(maximum=Decimal("1000")),
        allocation_profile=profile,
    )

    assert result.recommended_allocation == Decimal("620")


def test_minimum_recommended_allocation_can_raise_amount() -> None:
    profile = AllocationProfile(
        minimum_recommended_allocation=Decimal("500")
    )

    result = UniversalAllocationEngine().recommend(
        build_classification(DecisionAction.ACCUMULATE),
        build_confidence(0.25),
        build_constraints(maximum=Decimal("1000")),
        allocation_profile=profile,
    )

    assert result.recommended_allocation == Decimal("500")


def test_negative_requested_allocation_is_rejected() -> None:
    with pytest.raises(AllocationInputError):
        UniversalAllocationEngine().recommend(
            build_classification(),
            build_confidence(),
            build_constraints(),
            requested_allocation=Decimal("-1"),
        )


def test_asset_identifiers_must_match() -> None:
    with pytest.raises(AllocationInputError):
        UniversalAllocationEngine().recommend(
            build_classification(),
            build_confidence(asset_id="CRYPTO:BTC"),
            build_constraints(),
        )


def test_invalid_profile_ratio_is_rejected() -> None:
    with pytest.raises(AllocationConfigurationError):
        AllocationProfile(buy_multiplier=1.20)
