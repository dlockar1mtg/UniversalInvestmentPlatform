"""Service integration for forecast performance analytics."""

from __future__ import annotations

from datetime import date

from .forecast_archive import ForecastArchive
from .performance_contracts import (
    ForecastPerformanceReport,
    PerformanceAnalyticsProfile,
    PerformanceGrouping,
)
from .performance_engine import ForecastPerformanceAnalyticsEngine


class ForecastPerformanceAnalyticsService:
    """Build performance reports from archived validation records."""

    def __init__(
        self,
        *,
        archive: ForecastArchive,
        engine: ForecastPerformanceAnalyticsEngine | None = None,
    ) -> None:
        self.archive = archive
        self.engine = engine or ForecastPerformanceAnalyticsEngine()

    def report(
        self,
        *,
        grouping: PerformanceGrouping = PerformanceGrouping.OVERALL,
        profile: PerformanceAnalyticsProfile | None = None,
        evaluation_date: date | None = None,
    ) -> ForecastPerformanceReport:
        return self.engine.analyze(
            self.archive.all(),
            grouping=grouping,
            profile=profile,
            evaluation_date=evaluation_date,
        )

    def model_leaderboard(
        self,
        *,
        profile: PerformanceAnalyticsProfile | None = None,
        evaluation_date: date | None = None,
    ) -> ForecastPerformanceReport:
        return self.report(
            grouping=PerformanceGrouping.MODEL,
            profile=profile,
            evaluation_date=evaluation_date,
        )
