"""Binary signal normalization."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ..normalization import NormalizationResult
from ..normalization_strategy import NormalizationStrategy
from ..validation import validate_score


class BinaryNormalizer(NormalizationStrategy):
    strategy_name = "binary"

    def normalize(
        self,
        value: Any,
        *,
        true_score: Any = Decimal("100"),
        false_score: Any = Decimal("0"),
    ) -> NormalizationResult:
        if not isinstance(value, bool):
            raise TypeError("Binary normalization requires a bool value.")
        score = validate_score(true_score if value else false_score)
        return NormalizationResult(
            raw_value=value,
            normalized_score=score,
            strategy=self.strategy_name,
            diagnostics={"true_score": true_score, "false_score": false_score},
        )
