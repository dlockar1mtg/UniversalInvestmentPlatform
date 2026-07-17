"""Percentile-rank normalization."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable

from ..normalization import NormalizationResult
from ..normalization_strategy import NormalizationStrategy
from ..validation import to_decimal


class PercentileNormalizer(NormalizationStrategy):
    strategy_name = "percentile"

    def normalize(
        self,
        value: Any,
        *,
        population: Iterable[Any],
        higher_is_better: bool = True,
    ) -> NormalizationResult:
        raw = to_decimal(value, "value")
        values = tuple(to_decimal(item, "population item") for item in population)
        if not values:
            raise ValueError("population must not be empty.")

        less = sum(item < raw for item in values)
        equal = sum(item == raw for item in values)
        percentile = Decimal(str((less + (equal * 0.5)) / len(values))) * Decimal("100")
        score = percentile if higher_is_better else Decimal("100") - percentile

        return NormalizationResult(
            raw_value=raw,
            normalized_score=score,
            strategy=self.strategy_name,
            diagnostics={
                "population_size": len(values),
                "higher_is_better": higher_is_better,
            },
        )
