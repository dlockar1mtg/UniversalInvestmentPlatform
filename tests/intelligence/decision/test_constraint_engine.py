"""Tests for the Universal Constraint Engine."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from foundation.intelligence.decision import (
    ActionClassificationResult,
    ConfidenceBand,
    ConfidenceResult,
    ConstraintInputError,
    ConstraintStatus,
    DecisionAction,
    DecisionContext,
    DecisionEvidence,
    DecisionInput,
    EligibilityStatus,
    UniversalConstraintEngine,
)


def build_input(
    *,
    portfolio_value: Decimal = Decimal("100000"),
    available_capital: Decimal = Decimal("3000"),
    position_value: Decimal = Decimal("5000"),
    asset_weight: float = 0.05,
    class_weight: float = 0.20,
    target_asset_weight: float | None = None,
    target_class_weight: float | None = None,
    metadata: dict | None = None,
) -> DecisionInput:
    return DecisionInput(
        asset_id="ETF:VOO",
        asset_class="etf",
        time_horizon="3_year",
        context=DecisionContext(
            portfolio_id="PORTFOLIO-001",
            as_of=datetime.now(timezone.utc),
            portfolio_value=portfolio_value,
            available_capital=available_capital,
            current_position_value=position_value,
            current_asset_weight=asset_weight,
            current_asset_class_weight=class_weight,
            target_asset_weight=target_asset_weight,
            target_asset_class_weight=target_class_weight,
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
                description="Constraint evidence.",
            ),
        ),
        metadata=metadata or {},
    )


def build_classification(
    action: DecisionAction = DecisionAction.BUY,
    *,
    asset_id: str = "ETF:VOO",
) -> ActionClassificationResult:
    return ActionClassificationResult(
        asset_id=asset_id,
        action=action,
        eligibility=EligibilityStatus.ELIGIBLE,
        final_score=80.0,
        position_exists=True,
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


def test_constraints_allow_valid_buy() -> None:
    result = UniversalConstraintEngine().evaluate(
        build_input(),
        build_classification(),
        build_confidence(),
    )

    assert result.status is ConstraintStatus.PASSED
    assert result.maximum_permitted_allocation == Decimal("3000.00")
    assert result.binding_constraint == "available_capital"
    assert result.may_allocate is True


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
def test_non_increasing_actions_block_allocation(
    action: DecisionAction,
) -> None:
    result = UniversalConstraintEngine().evaluate(
        build_input(),
        build_classification(action),
        build_confidence(),
    )

    assert result.status is ConstraintStatus.BLOCKED
    assert result.maximum_permitted_allocation == Decimal("0.00")


def test_zero_available_capital_blocks_allocation() -> None:
    result = UniversalConstraintEngine().evaluate(
        build_input(available_capital=Decimal("0")),
        build_classification(),
        build_confidence(),
    )

    assert result.status is ConstraintStatus.BLOCKED


def test_asset_capacity_can_be_binding() -> None:
    result = UniversalConstraintEngine().evaluate(
        build_input(
            available_capital=Decimal("10000"),
            position_value=Decimal("18000"),
            asset_weight=0.18,
        ),
        build_classification(),
        build_confidence(),
    )

    assert result.maximum_permitted_allocation == Decimal("2000.00")
    assert result.binding_constraint == "asset_weight_capacity"


def test_asset_class_capacity_can_be_binding() -> None:
    result = UniversalConstraintEngine().evaluate(
        build_input(
            available_capital=Decimal("10000"),
            class_weight=0.48,
        ),
        build_classification(),
        build_confidence(),
    )

    assert result.maximum_permitted_allocation == Decimal("2000.00")
    assert result.binding_constraint == "asset_class_weight_capacity"


def test_target_asset_gap_can_limit_allocation() -> None:
    result = UniversalConstraintEngine().evaluate(
        build_input(
            available_capital=Decimal("10000"),
            position_value=Decimal("5000"),
            target_asset_weight=0.08,
        ),
        build_classification(),
        build_confidence(),
    )

    assert result.maximum_permitted_allocation == Decimal("3000.00")
    assert result.binding_constraint == "target_asset_gap"


def test_target_asset_at_limit_creates_zero_capacity() -> None:
    result = UniversalConstraintEngine().evaluate(
        build_input(
            position_value=Decimal("10000"),
            target_asset_weight=0.10,
        ),
        build_classification(),
        build_confidence(),
    )

    assert result.maximum_permitted_allocation == Decimal("0.00")
    assert result.status is ConstraintStatus.WARNING
    assert result.may_allocate is False


def test_low_confidence_creates_warning() -> None:
    result = UniversalConstraintEngine().evaluate(
        build_input(),
        build_classification(),
        build_confidence(0.55),
    )

    assert result.status is ConstraintStatus.WARNING
    assert result.maximum_permitted_allocation == Decimal("3000.00")


def test_explicit_prohibition_blocks_allocation() -> None:
    result = UniversalConstraintEngine().evaluate(
        build_input(
            metadata={"allocation_prohibited": True}
        ),
        build_classification(),
        build_confidence(),
    )

    assert result.status is ConstraintStatus.BLOCKED
    assert result.maximum_permitted_allocation == Decimal("0.00")


def test_liquidity_limit_can_be_binding() -> None:
    result = UniversalConstraintEngine().evaluate(
        build_input(
            metadata={"liquidity_allocation_limit": "750"}
        ),
        build_classification(),
        build_confidence(),
    )

    assert result.maximum_permitted_allocation == Decimal("750.00")
    assert result.binding_constraint == "liquidity_allocation_limit"


def test_invalid_liquidity_limit_is_rejected() -> None:
    with pytest.raises(ConstraintInputError):
        UniversalConstraintEngine().evaluate(
            build_input(
                metadata={"liquidity_allocation_limit": "invalid"}
            ),
            build_classification(),
            build_confidence(),
        )


def test_asset_identifiers_must_match() -> None:
    with pytest.raises(ConstraintInputError):
        UniversalConstraintEngine().evaluate(
            build_input(),
            build_classification(asset_id="CRYPTO:BTC"),
            build_confidence(),
        )
