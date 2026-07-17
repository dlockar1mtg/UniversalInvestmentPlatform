"""Portfolio concentration metrics."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


@dataclass(slots=True)
class ConcentrationResult:
    largest_weight: Decimal
    top_three_weight: Decimal
    herfindahl_index: Decimal
    effective_holding_count: Decimal


def calculate_concentration(weights: Iterable[Decimal]) -> ConcentrationResult:
    normalized = sorted(
        (Decimal(str(weight)) for weight in weights if Decimal(str(weight)) > 0),
        reverse=True,
    )
    if not normalized:
        return ConcentrationResult(
            largest_weight=Decimal("0"),
            top_three_weight=Decimal("0"),
            herfindahl_index=Decimal("0"),
            effective_holding_count=Decimal("0"),
        )

    hhi = sum((weight * weight for weight in normalized), Decimal("0"))
    return ConcentrationResult(
        largest_weight=normalized[0],
        top_three_weight=sum(normalized[:3], Decimal("0")),
        herfindahl_index=hhi,
        effective_holding_count=Decimal("0") if hhi == 0 else Decimal("1") / hhi,
    )
