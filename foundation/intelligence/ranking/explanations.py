"""Deterministic, portfolio-relative explanations for ranking outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from .competition import CompetitionDisposition, CompetitionOutcome


def _decimal_map(values: Mapping[str, object]) -> dict[str, Decimal]:
    converted: dict[str, Decimal] = {}
    for name, value in values.items():
        converted[str(name)] = Decimal(str(value))
    return converted


def _label(name: str) -> str:
    return name.replace("_", " ").strip().title()


@dataclass(frozen=True)
class ExplanationDriver:
    factor_name: str
    factor_value: Decimal
    direction: str
    statement: str


@dataclass(frozen=True)
class RankingExplanation:
    opportunity_id: str
    rank: int
    disposition: str
    headline: str
    summary: str
    positive_drivers: tuple[ExplanationDriver, ...]
    limiting_drivers: tuple[ExplanationDriver, ...]
    portfolio_statement: str
    audit_evidence: Mapping[str, object] = field(default_factory=dict)


def build_ranking_explanation(
    outcome: CompetitionOutcome,
    factor_scores: Mapping[str, object],
    *,
    penalties: Mapping[str, object] | None = None,
    portfolio_context: Mapping[str, object] | None = None,
    max_drivers: int = 3,
) -> RankingExplanation:
    """Build an immutable explanation without recalculating the ranking.

    Factor values are treated as already-normalized ranking evidence. Positive
    drivers are the highest values; limiting drivers are explicit penalties,
    followed by the lowest factors when no penalty exists.
    """
    if max_drivers < 1:
        raise ValueError("max_drivers must be at least 1")
    factors = _decimal_map(factor_scores)
    penalty_values = _decimal_map(penalties or {})
    context = dict(portfolio_context or {})

    descending = sorted(factors.items(), key=lambda item: (-item[1], item[0]))
    positive = tuple(
        ExplanationDriver(
            factor_name=name,
            factor_value=value,
            direction="POSITIVE",
            statement=f"{_label(name)} contributed {value} to ranking strength.",
        )
        for name, value in descending[:max_drivers]
    )

    active_penalties = sorted(
        ((name, value) for name, value in penalty_values.items() if value > 0),
        key=lambda item: (-item[1], item[0]),
    )
    limiting_source = active_penalties or sorted(
        factors.items(), key=lambda item: (item[1], item[0])
    )
    limiting = tuple(
        ExplanationDriver(
            factor_name=name,
            factor_value=value,
            direction="LIMITING",
            statement=(
                f"{_label(name)} applied a {value} priority penalty."
                if active_penalties
                else f"{_label(name)} was a comparatively weaker factor at {value}."
            ),
        )
        for name, value in limiting_source[:max_drivers]
    )

    disposition = outcome.disposition.value
    reason = outcome.reason_code.value
    if outcome.disposition is CompetitionDisposition.SELECTED:
        headline = f"Selected at portfolio rank {outcome.rank}"
        summary = "The opportunity remained within all active selection constraints."
    elif outcome.disposition is CompetitionDisposition.DEFERRED:
        headline = f"Deferred at portfolio rank {outcome.rank}"
        summary = f"The opportunity remains valid but was deferred: {reason}."
    elif outcome.disposition is CompetitionDisposition.SUPPRESSED:
        headline = f"Suppressed at portfolio rank {outcome.rank}"
        summary = (
            f"The opportunity lost direct competition to {outcome.competed_with}: {reason}."
        )
    else:
        headline = f"Excluded at portfolio rank {outcome.rank}"
        summary = f"The opportunity was not eligible for selection: {reason}."

    if context:
        context_text = ", ".join(
            f"{_label(str(name))}: {context[name]}" for name in sorted(context)
        )
        portfolio_statement = f"Portfolio context — {context_text}."
    else:
        portfolio_statement = "No additional portfolio-context evidence was supplied."

    audit = MappingProxyType(
        {
            "priority_score": str(outcome.priority_score),
            "reason_code": reason,
            "competed_with": outcome.competed_with,
            "factor_scores": MappingProxyType({k: str(v) for k, v in sorted(factors.items())}),
            "penalties": MappingProxyType(
                {k: str(v) for k, v in sorted(penalty_values.items())}
            ),
            "portfolio_context": MappingProxyType(
                {str(k): context[k] for k in sorted(context)}
            ),
            "competition_evidence": MappingProxyType(dict(outcome.evidence)),
        }
    )
    return RankingExplanation(
        opportunity_id=outcome.opportunity_id,
        rank=outcome.rank,
        disposition=disposition,
        headline=headline,
        summary=summary,
        positive_drivers=positive,
        limiting_drivers=limiting,
        portfolio_statement=portfolio_statement,
        audit_evidence=audit,
    )
