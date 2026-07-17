"""Dashboard-ready validation dataset builders."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from .validation_reporting import ExecutiveValidationReport


@dataclass(frozen=True, slots=True)
class DashboardValidationDataset:
    """Flat records and summary KPIs for validation dashboards."""

    scorecard_rows: tuple[Mapping[str, object], ...]
    summary_kpis: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "scorecard_rows",
            tuple(MappingProxyType(dict(row)) for row in self.scorecard_rows),
        )
        object.__setattr__(
            self,
            "summary_kpis",
            MappingProxyType(dict(self.summary_kpis)),
        )


def build_dashboard_dataset(
    report: ExecutiveValidationReport,
) -> DashboardValidationDataset:
    rows = tuple(
        {
            "asset_class": item.asset_class,
            "model_id": item.model_id,
            "model_version": item.model_version,
            "horizon_days": item.horizon_days,
            "certification_status": item.certification_status,
            "validation_grade": item.validation_grade,
            "validation_score": item.validation_score,
            "rank": item.rank,
            "headline": item.headline,
            "key_strengths": " | ".join(item.key_strengths),
            "key_risks": " | ".join(item.key_risks),
            "warning_count": len(item.warnings),
        }
        for item in report.scorecards
    )

    certified = sum(
        item.certification_status == "certified"
        for item in report.scorecards
    )
    average_score = (
        sum(
            (item.validation_score for item in report.scorecards),
            Decimal("0"),
        )
        / Decimal(len(report.scorecards))
        if report.scorecards
        else None
    )

    summary = {
        "overall_status": report.overall_status,
        "asset_class_count": len(report.scorecards),
        "certified_model_count": certified,
        "certification_rate": (
            Decimal(certified) / Decimal(len(report.scorecards))
            if report.scorecards
            else None
        ),
        "average_validation_score": average_score,
        "horizon_days": report.horizon_days,
        "methodology_version": report.methodology_version,
    }

    return DashboardValidationDataset(
        scorecard_rows=rows,
        summary_kpis=summary,
    )
