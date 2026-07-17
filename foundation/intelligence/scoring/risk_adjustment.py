"""Risk adjustment policies."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .validation import validate_score, validate_unit_interval


@dataclass(frozen=True, slots=True)
class RiskAdjustment:
    input_score: Decimal
    risk_score: Decimal
    maximum_risk_penalty: Decimal
    risk_penalty_ratio: Decimal
    multiplier: Decimal
    adjusted_score: Decimal

    def __post_init__(self) -> None:
        for field_name in ("input_score", "risk_score", "adjusted_score"):
            object.__setattr__(
                self,
                field_name,
                validate_score(getattr(self, field_name), field_name),
            )
        for field_name in (
            "maximum_risk_penalty",
            "risk_penalty_ratio",
            "multiplier",
        ):
            object.__setattr__(
                self,
                field_name,
                validate_unit_interval(getattr(self, field_name), field_name),
            )


def apply_risk_adjustment(
    input_score: Decimal,
    risk_score: Decimal,
    maximum_risk_penalty: Decimal,
) -> RiskAdjustment:
    """Penalize lower risk-dimension scores while preserving a bounded floor."""
    score = validate_score(input_score, "input_score")
    risk = validate_score(risk_score, "risk_score")
    maximum_penalty = validate_unit_interval(
        maximum_risk_penalty,
        "maximum_risk_penalty",
    )
    risk_penalty_ratio = (Decimal("100") - risk) / Decimal("100")
    multiplier = Decimal("1") - maximum_penalty * risk_penalty_ratio
    adjusted = score * multiplier
    return RiskAdjustment(
        input_score=score,
        risk_score=risk,
        maximum_risk_penalty=maximum_penalty,
        risk_penalty_ratio=risk_penalty_ratio,
        multiplier=multiplier,
        adjusted_score=adjusted,
    )
