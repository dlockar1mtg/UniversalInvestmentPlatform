"""Validation reporting contracts and executive summaries."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from .certification_evaluator import ModelCertificationDecision
from .cross_asset_contracts import CrossAssetValidationReport


@dataclass(frozen=True, slots=True)
class ValidationScorecard:
    """Dashboard-ready model validation scorecard."""

    asset_class: str
    model_id: str
    model_version: str
    horizon_days: int
    certification_status: str
    validation_grade: str
    validation_score: Decimal
    rank: int
    headline: str
    key_strengths: tuple[str, ...]
    key_risks: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExecutiveValidationReport:
    """Human-readable and machine-readable Phase 3.2 report."""

    title: str
    horizon_days: int
    overall_status: str
    executive_summary: str
    scorecards: tuple[ValidationScorecard, ...]
    certification_decisions: Mapping[str, ModelCertificationDecision]
    methodology_version: str
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "certification_decisions",
            MappingProxyType(dict(self.certification_decisions)),
        )


def _strengths(component_scores: Mapping[str, Decimal]) -> tuple[str, ...]:
    ordered = sorted(
        component_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    return tuple(
        name.replace("_", " ").title()
        for name, score in ordered[:3]
        if score >= Decimal("60")
    )


def _risks(
    component_scores: Mapping[str, Decimal],
    penalties: Mapping[str, Decimal],
) -> tuple[str, ...]:
    risks = [
        name.replace("_", " ").title()
        for name, score in sorted(component_scores.items(), key=lambda item: item[1])
        if score < Decimal("50")
    ][:3]
    risks.extend(
        f"{name.replace('_', ' ').title()} penalty"
        for name in penalties
    )
    return tuple(dict.fromkeys(risks))


def build_executive_report(
    cross_asset_report: CrossAssetValidationReport,
    decisions: Mapping[str, ModelCertificationDecision],
) -> ExecutiveValidationReport:
    """Build an executive validation report from grades and certification decisions."""
    scorecards = []
    for grade in cross_asset_report.grades:
        decision = decisions.get(grade.asset_class)
        status = (
            "certified"
            if decision is not None and decision.passed
            else "not_certified"
        )
        headline = (
            f"{grade.asset_class.title()} model earned a {grade.grade} "
            f"validation grade and is {status.replace('_', ' ')}."
        )
        scorecards.append(
            ValidationScorecard(
                asset_class=grade.asset_class,
                model_id=(
                    decision.model_id
                    if decision is not None
                    else "unknown"
                ),
                model_version=(
                    decision.model_version
                    if decision is not None
                    else "unknown"
                ),
                horizon_days=grade.horizon_days,
                certification_status=status,
                validation_grade=grade.grade,
                validation_score=grade.adjusted_score,
                rank=grade.rank,
                headline=headline,
                key_strengths=_strengths(grade.component_scores),
                key_risks=_risks(grade.component_scores, grade.penalties),
                warnings=tuple(
                    dict.fromkeys(
                        grade.limitations
                        + (() if decision is None else decision.warnings)
                    )
                ),
            )
        )

    certified_count = sum(
        decision.passed for decision in decisions.values()
    )
    overall_status = (
        "certified"
        if decisions and certified_count == len(decisions)
        else "partially_certified"
        if certified_count > 0
        else "not_certified"
    )
    executive_summary = (
        f"Phase 3.2 evaluated {len(scorecards)} asset classes at the "
        f"{cross_asset_report.horizon_days}-day horizon. "
        f"{certified_count} of {len(decisions)} models met all configured "
        f"certification thresholds."
    )

    return ExecutiveValidationReport(
        title="Universal Investment Platform Historical Validation Report",
        horizon_days=cross_asset_report.horizon_days,
        overall_status=overall_status,
        executive_summary=executive_summary,
        scorecards=tuple(scorecards),
        certification_decisions=decisions,
        methodology_version=cross_asset_report.methodology_version,
        warnings=cross_asset_report.warnings,
    )
