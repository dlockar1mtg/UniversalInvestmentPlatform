"""Build score components from asset-class profile metric rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from .asset_profile import AssetClassScoringProfile
from .normalization_engine import NormalizationEngine
from .score_component import DataAvailability, ScoreComponent


@dataclass(frozen=True, slots=True)
class MetricObservation:
    """Observed raw metric value and data-quality state."""

    value: Any
    availability: DataAvailability = DataAvailability.AVAILABLE
    confidence: Decimal = Decimal("1")
    source: str = "unknown"
    warning: str | None = None


class AssetProfileScoringService:
    """Convert observed metrics into universal ScoreComponent records."""

    def __init__(self, normalization_engine: NormalizationEngine | None = None) -> None:
        self._normalization_engine = normalization_engine or NormalizationEngine()

    def build_components(
        self,
        profile: AssetClassScoringProfile,
        observations: Mapping[str, MetricObservation],
    ) -> tuple[ScoreComponent, ...]:
        components: list[ScoreComponent] = []

        for rule in profile.metric_rules:
            observation = observations.get(rule.metric_name)
            if observation is None:
                observation = MetricObservation(
                    value=None,
                    availability=DataAvailability.UNAVAILABLE,
                    confidence=Decimal("0"),
                    source="missing",
                    warning="Metric observation was not supplied.",
                )

            result = self._normalization_engine.normalize(
                rule.strategy,
                observation.value,
                availability=observation.availability,
                warning=observation.warning,
                **dict(rule.parameters),
            )
            combined_confidence = min(rule.confidence, observation.confidence)

            components.append(
                ScoreComponent(
                    metric_name=rule.metric_name,
                    dimension=rule.dimension,
                    availability=result.availability,
                    raw_value=(
                        observation.value
                        if isinstance(observation.value, (int, float, str, Decimal))
                        and not isinstance(observation.value, bool)
                        else None
                    ),
                    normalized_score=result.normalized_score,
                    weight=rule.weight,
                    confidence=combined_confidence,
                    source=observation.source,
                    calculation_method=rule.strategy,
                    warning=result.warning or observation.warning,
                )
            )

        return tuple(components)
