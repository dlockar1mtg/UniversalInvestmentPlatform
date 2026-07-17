"""Historical analog similarity ranking."""

from __future__ import annotations

from collections.abc import Iterable
from math import sqrt

from .calibration_contracts import MarketRegime
from .explainability_contracts import HistoricalAnalog


class HistoricalSimilarityEngine:
    """Rank historical contexts using weighted normalized feature distance."""

    def rank(
        self,
        *,
        current_features: dict[str, float],
        candidates: Iterable[
            tuple[str, str, MarketRegime, str, dict[str, float]]
        ],
        feature_weights: dict[str, float] | None = None,
        limit: int = 3,
    ) -> tuple[HistoricalAnalog, ...]:
        if not current_features:
            return ()
        if limit <= 0:
            raise ValueError("limit must be positive.")

        weights = feature_weights or {
            name: 1.0 for name in current_features
        }
        if any(weight < 0 for weight in weights.values()):
            raise ValueError("feature weights cannot be negative.")

        ranked: list[HistoricalAnalog] = []
        for analog_id, label, regime, outcome, features in candidates:
            common = sorted(set(current_features) & set(features))
            if not common:
                continue

            weighted_squared_error = 0.0
            weight_total = 0.0
            feature_similarity: dict[str, float] = {}

            for name in common:
                weight = float(weights.get(name, 1.0))
                difference = abs(
                    float(current_features[name]) - float(features[name])
                )
                similarity = max(0.0, 1.0 - difference)
                feature_similarity[name] = similarity
                weighted_squared_error += weight * difference**2
                weight_total += weight

            if weight_total == 0:
                continue

            distance = sqrt(weighted_squared_error / weight_total)
            overall = max(0.0, 1.0 - distance)
            ranked.append(
                HistoricalAnalog(
                    analog_id=analog_id,
                    label=label,
                    similarity_score=overall,
                    regime=regime,
                    outcome_summary=outcome,
                    feature_similarity=feature_similarity,
                )
            )

        ranked.sort(
            key=lambda item: (
                -item.similarity_score,
                item.analog_id,
            )
        )
        return tuple(ranked[:limit])
