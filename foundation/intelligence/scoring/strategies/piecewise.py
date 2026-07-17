"""Piecewise-linear normalization."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable

from ..normalization import NormalizationResult, clip_decimal
from ..normalization_strategy import NormalizationStrategy
from ..validation import to_decimal, validate_score


class PiecewiseNormalizer(NormalizationStrategy):
    strategy_name = "piecewise"

    def normalize(
        self,
        value: Any,
        *,
        points: Iterable[tuple[Any, Any]],
        clip: bool = True,
    ) -> NormalizationResult:
        raw = to_decimal(value, "value")
        normalized_points = tuple(
            sorted(
                (
                    to_decimal(x, "point value"),
                    validate_score(y, "point score"),
                )
                for x, y in points
            )
        )
        if len(normalized_points) < 2:
            raise ValueError("At least two piecewise points are required.")
        x_values = [item[0] for item in normalized_points]
        if len(x_values) != len(set(x_values)):
            raise ValueError("Piecewise point values must be unique.")

        low, high = normalized_points[0][0], normalized_points[-1][0]
        working = raw
        clipped = False
        if clip:
            working, clipped = clip_decimal(raw, low, high)
        elif raw < low or raw > high:
            raise ValueError("value is outside the piecewise range.")

        for (x1, y1), (x2, y2) in zip(normalized_points, normalized_points[1:]):
            if x1 <= working <= x2:
                ratio = (working - x1) / (x2 - x1)
                score = y1 + ratio * (y2 - y1)
                break
        else:
            score = normalized_points[-1][1]

        return NormalizationResult(
            raw_value=raw,
            normalized_score=score,
            strategy=self.strategy_name,
            clipped=clipped,
            warning="Value clipped to piecewise range." if clipped else None,
            diagnostics={"points": normalized_points},
        )
