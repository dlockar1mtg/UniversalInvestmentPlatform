"""Service orchestration for continuous forecast learning."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .forecast_archive import ForecastArchive
from .learning_contracts import (
    ContinuousLearningProfile,
    ContinuousLearningResult,
    LearningState,
)
from .learning_engine import ContinuousLearningEngine
from .learning_state import (
    load_learning_state,
    save_learning_state,
)
from .performance_contracts import (
    PerformanceAnalyticsProfile,
    PerformanceGrouping,
)
from .performance_engine import ForecastPerformanceAnalyticsEngine


class ContinuousLearningService:
    """Run performance analytics and persist adaptive learning state."""

    def __init__(
        self,
        *,
        archive: ForecastArchive,
        performance_engine: ForecastPerformanceAnalyticsEngine | None = None,
        learning_engine: ContinuousLearningEngine | None = None,
    ) -> None:
        self.archive = archive
        self.performance_engine = (
            performance_engine or ForecastPerformanceAnalyticsEngine()
        )
        self.learning_engine = (
            learning_engine or ContinuousLearningEngine()
        )

    def learn_from_archive(
        self,
        *,
        current_weights: dict[str, float] | None = None,
        prior_state: LearningState | None = None,
        performance_profile: PerformanceAnalyticsProfile | None = None,
        learning_profile: ContinuousLearningProfile | None = None,
        evaluation_date: date | None = None,
    ) -> ContinuousLearningResult:
        report = self.performance_engine.analyze(
            self.archive.all(),
            grouping=PerformanceGrouping.MODEL,
            profile=performance_profile,
            evaluation_date=evaluation_date,
        )
        return self.learning_engine.learn(
            report.scorecards,
            current_weights=current_weights,
            prior_state=prior_state,
            profile=learning_profile,
            as_of_date=evaluation_date,
        )

    def learn_and_save(
        self,
        path: str | Path,
        **kwargs,
    ) -> ContinuousLearningResult:
        result = self.learn_from_archive(**kwargs)
        save_learning_state(result.state, path)
        return result

    @staticmethod
    def load_state(path: str | Path) -> LearningState:
        return load_learning_state(path)
