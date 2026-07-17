"""Service orchestration for forecast drift detection."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .drift_contracts import (
    DriftDetectionProfile,
    DriftHistory,
    ForecastDriftReport,
)
from .drift_engine import ForecastDriftDetectionEngine
from .drift_history import (
    load_drift_history,
    save_drift_history,
)
from .forecast_archive import ForecastArchive
from .performance_contracts import (
    PerformanceAnalyticsProfile,
    PerformanceGrouping,
)
from .performance_engine import ForecastPerformanceAnalyticsEngine


class ForecastDriftDetectionService:
    """Build scorecard windows and run drift detection."""

    def __init__(
        self,
        *,
        baseline_archive: ForecastArchive,
        current_archive: ForecastArchive,
        performance_engine: ForecastPerformanceAnalyticsEngine | None = None,
        drift_engine: ForecastDriftDetectionEngine | None = None,
    ) -> None:
        self.baseline_archive = baseline_archive
        self.current_archive = current_archive
        self.performance_engine = (
            performance_engine or ForecastPerformanceAnalyticsEngine()
        )
        self.drift_engine = (
            drift_engine or ForecastDriftDetectionEngine()
        )

    def detect(
        self,
        *,
        baseline_regime: str = "unknown",
        current_regime: str = "unknown",
        prior_history: DriftHistory | None = None,
        performance_profile: PerformanceAnalyticsProfile | None = None,
        drift_profile: DriftDetectionProfile | None = None,
        evaluation_date: date | None = None,
    ) -> ForecastDriftReport:
        baseline_report = self.performance_engine.analyze(
            self.baseline_archive.all(),
            grouping=PerformanceGrouping.MODEL,
            profile=performance_profile,
            evaluation_date=evaluation_date,
        )
        current_report = self.performance_engine.analyze(
            self.current_archive.all(),
            grouping=PerformanceGrouping.MODEL,
            profile=performance_profile,
            evaluation_date=evaluation_date,
        )
        return self.drift_engine.detect(
            baseline_report.scorecards,
            current_report.scorecards,
            baseline_regime=baseline_regime,
            current_regime=current_regime,
            prior_history=prior_history,
            profile=drift_profile,
            as_of_date=evaluation_date,
        )

    def detect_and_save(
        self,
        path: str | Path,
        **kwargs,
    ) -> ForecastDriftReport:
        report = self.detect(**kwargs)
        save_drift_history(report.history, path)
        return report

    @staticmethod
    def load_history(path: str | Path) -> DriftHistory:
        return load_drift_history(path)
