"""Linear lower-is-better normalization."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ..normalization import NormalizationResult, clip_decimal
from ..normalization_strategy import NormalizationStrategy
from ..validation import to_decimal


class LowerIsBetterNormalizer(NormalizationStrategy):
    strategy_name = "lower_is_better"

    def normalize(
        self,
        value: Any,
        *,
        minimum: Any,
        maximum: Any,
        clip: bool = True,
    ) -> NormalizationResult:
        raw = to_decimal(value, "value")
        low = to_decimal(minimum, "minimum")
        high = to_decimal(maximum, "maximum")
        if low >= high:
            raise ValueError("minimum must be less than maximum.")

        working = raw
        clipped = False
        if clip:
            working, clipped = clip_decimal(raw, low, high)
        elif raw < low or raw > high:
            raise ValueError("value is outside the allowed range.")

        score = Decimal("100") * (high - working) / (high - low)
        return NormalizationResult(
            raw_value=raw,
            normalized_score=score,
            strategy=self.strategy_name,
            clipped=clipped,
            warning="Value clipped to configured range." if clipped else None,
            diagnostics={"minimum": low, "maximum": high},
        )
