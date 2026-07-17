"""Service integration for distribution-risk analytics."""

from __future__ import annotations

from collections.abc import Iterable

from .distribution_models import ForecastDistributionResult
from .risk_analytics_contracts import (
    DistributionComparisonResult,
    DistributionRiskMetrics,
    DistributionRiskProfile,
)
from .risk_analytics_engine import DistributionRiskAnalyticsEngine


class DistributionRiskAnalyticsService:
    """Analyze and compare canonical forecast distributions."""

    def __init__(
        self,
        engine: DistributionRiskAnalyticsEngine | None = None,
    ) -> None:
        self.engine = engine or DistributionRiskAnalyticsEngine()

    def analyze_distribution(
        self,
        distribution: ForecastDistributionResult,
        *,
        profile: DistributionRiskProfile | None = None,
        samples: Iterable[float] | None = None,
        probabilities: Iterable[float] | None = None,
    ) -> DistributionRiskMetrics:
        return self.engine.analyze(
            distribution,
            profile=profile,
            samples=samples,
            probabilities=probabilities,
        )

    def compare_distributions(
        self,
        distributions: Iterable[ForecastDistributionResult],
        *,
        profile: DistributionRiskProfile | None = None,
    ) -> DistributionComparisonResult:
        metrics = tuple(
            self.analyze_distribution(
                distribution,
                profile=profile,
            )
            for distribution in distributions
        )
        return self.engine.compare(metrics)
