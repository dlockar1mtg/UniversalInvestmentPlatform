from decimal import Decimal

from foundation.intelligence.scoring import (
    apply_confidence_adjustment,
    apply_risk_adjustment,
)


def test_confidence_adjustment_uses_floor() -> None:
    result = apply_confidence_adjustment(
        Decimal("80"),
        Decimal("0"),
        Decimal("0.70"),
    )
    assert result.multiplier == Decimal("0.70")
    assert result.adjusted_score == Decimal("56.00")


def test_full_confidence_preserves_score() -> None:
    result = apply_confidence_adjustment(
        Decimal("80"),
        Decimal("100"),
        Decimal("0.70"),
    )
    assert result.multiplier == Decimal("1.00")
    assert result.adjusted_score == Decimal("80.00")


def test_zero_risk_score_applies_maximum_penalty() -> None:
    result = apply_risk_adjustment(
        Decimal("80"),
        Decimal("0"),
        Decimal("0.20"),
    )
    assert result.multiplier == Decimal("0.80")
    assert result.adjusted_score == Decimal("64.00")


def test_perfect_risk_score_applies_no_penalty() -> None:
    result = apply_risk_adjustment(
        Decimal("80"),
        Decimal("100"),
        Decimal("0.20"),
    )
    assert result.multiplier == Decimal("1.00")
    assert result.adjusted_score == Decimal("80.00")
