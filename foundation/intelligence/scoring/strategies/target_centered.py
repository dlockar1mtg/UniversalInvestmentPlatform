"""Target-centered normalization where proximity to a target is best."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ..normalization import NormalizationResult, clip_decimal
from ..normalization_strategy import NormalizationStrategy
from ..validation import to_decimal


class TargetCenteredNormalizer(NormalizationStrategy):
    strategy_name = "target_centered"

    def normalize(
        self,
        value: Any,
        *,
        minimum: Any,
        target: Any,
        maximum: Any,
        clip: bool = True,
    ) -> NormalizationResult:
        raw = to_decimal(value, "value")
        low = to_decimal(minimum, "minimum")
        target_value = to_decimal(target, "target")
        high = to_decimal(maximum, "maximum")
        if not low < target_value < high:
            raise ValueError("target must be strictly between minimum and maximum.")

        working = raw
        clipped = False
        if clip:
            working, clipped = clip_decimal(raw, low, high)
        elif raw < low or raw > high:
            raise ValueError("value is outside the allowed range.")

        if working <= target_value:
            score = Decimal("100") * (working - low) / (target_value - low)
        else:
            score = Decimal("100") * (high - working) / (high - target_value)

        return NormalizationResult(
            raw_value=raw,
            normalized_score=score,
            strategy=self.strategy_name,
            clipped=clipped,
            warning="Value clipped to configured range." if clipped else None,
            diagnostics={"minimum": low, "target": target_value, "maximum": high},
        )
