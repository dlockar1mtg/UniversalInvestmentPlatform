"""Normalization for metrics already bounded by a known interval."""

from __future__ import annotations

from typing import Any

from .higher_is_better import HigherIsBetterNormalizer


class BoundedRangeNormalizer(HigherIsBetterNormalizer):
    strategy_name = "bounded_range"

    def normalize(self, value: Any, *, minimum: Any, maximum: Any, clip: bool = True):
        result = super().normalize(value, minimum=minimum, maximum=maximum, clip=clip)
        return type(result)(
            raw_value=result.raw_value,
            normalized_score=result.normalized_score,
            strategy=self.strategy_name,
            availability=result.availability,
            clipped=result.clipped,
            warning=result.warning,
            diagnostics=result.diagnostics,
        )
