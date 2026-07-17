"""Categorical lookup normalization."""

from __future__ import annotations

from typing import Any, Mapping

from ..normalization import NormalizationResult
from ..normalization_strategy import NormalizationStrategy
from ..validation import validate_score


class CategoricalNormalizer(NormalizationStrategy):
    strategy_name = "categorical"

    def normalize(
        self,
        value: Any,
        *,
        scores: Mapping[Any, Any],
        case_sensitive: bool = False,
    ) -> NormalizationResult:
        if not scores:
            raise ValueError("scores mapping must not be empty.")

        lookup = dict(scores)
        key = value
        if isinstance(value, str) and not case_sensitive:
            lookup = {
                item_key.casefold() if isinstance(item_key, str) else item_key: item_value
                for item_key, item_value in lookup.items()
            }
            key = value.casefold()

        if key not in lookup:
            raise ValueError(f"No categorical score configured for {value!r}.")

        score = validate_score(lookup[key], "categorical score")
        return NormalizationResult(
            raw_value=value,
            normalized_score=score,
            strategy=self.strategy_name,
            diagnostics={"case_sensitive": case_sensitive},
        )
