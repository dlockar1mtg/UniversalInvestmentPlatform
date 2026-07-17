"""Service orchestration for forecast certification."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .certification_contracts import (
    ForecastCertificationProfile,
    ForecastCertificationReport,
)
from .certification_engine import ForecastCertificationEngine
from .certification_state import (
    load_certification_report,
    save_certification_report,
)
from .drift_contracts import ForecastDriftReport
from .learning_contracts import ContinuousLearningResult
from .performance_contracts import ForecastPerformanceReport


class ForecastCertificationService:
    """Certify models from performance, learning, and drift reports."""

    def __init__(
        self,
        engine: ForecastCertificationEngine | None = None,
    ) -> None:
        self.engine = engine or ForecastCertificationEngine()

    def certify(
        self,
        *,
        performance_report: ForecastPerformanceReport,
        learning_result: ContinuousLearningResult,
        drift_report: ForecastDriftReport,
        profile: ForecastCertificationProfile | None = None,
        effective_date: date | None = None,
    ) -> ForecastCertificationReport:
        return self.engine.certify(
            performance_report.scorecards,
            learning_result.signals,
            drift_report.signals,
            profile=profile,
            effective_date=effective_date,
        )

    def certify_and_save(
        self,
        path: str | Path,
        **kwargs,
    ) -> ForecastCertificationReport:
        report = self.certify(**kwargs)
        save_certification_report(report, path)
        return report

    @staticmethod
    def load_report(
        path: str | Path,
    ) -> ForecastCertificationReport:
        return load_certification_report(path)
