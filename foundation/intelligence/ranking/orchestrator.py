"""Deterministic portfolio-ranking batch orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Iterable, Mapping

from .competition import (
    CompetitionCandidate,
    CompetitionOutcome,
    CompetitionPolicy,
    resolve_competition,
)
from .explanations import RankingExplanation, build_ranking_explanation


def _freeze(values: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType({str(key): values[key] for key in sorted(values)})


@dataclass(frozen=True)
class PortfolioRankingItem:
    """Normalized handoff from comparability, context, factors, and priority."""

    opportunity_id: str
    priority_score: Decimal | float | int
    priority_tier: str
    factor_scores: Mapping[str, object]
    comparability_status: str = "COMPARABLE"
    penalties: Mapping[str, object] = field(default_factory=dict)
    portfolio_context: Mapping[str, object] = field(default_factory=dict)
    group_key: str = "UNGROUPED"
    duplicate_key: str | None = None

    def __post_init__(self) -> None:
        if not self.opportunity_id.strip():
            raise ValueError("opportunity_id must not be blank")
        if not self.priority_tier.strip():
            raise ValueError("priority_tier must not be blank")
        if not self.factor_scores:
            raise ValueError("factor_scores must not be empty")
        object.__setattr__(self, "priority_score", Decimal(str(self.priority_score)))
        object.__setattr__(self, "factor_scores", _freeze(self.factor_scores))
        object.__setattr__(self, "penalties", _freeze(self.penalties))
        object.__setattr__(self, "portfolio_context", _freeze(self.portfolio_context))


@dataclass(frozen=True)
class RankingArtifact:
    opportunity_id: str
    stage: str
    sequence: int
    evidence: Mapping[str, object]


@dataclass(frozen=True)
class PortfolioRankingBatchResult:
    batch_id: str
    batch_fingerprint: str
    outcomes: tuple[CompetitionOutcome, ...]
    explanations: tuple[RankingExplanation, ...]
    artifacts: tuple[RankingArtifact, ...]

    @property
    def selected(self) -> tuple[CompetitionOutcome, ...]:
        return tuple(item for item in self.outcomes if item.disposition.value == "SELECTED")


def _fingerprint(batch_id: str, items: tuple[PortfolioRankingItem, ...], policy: CompetitionPolicy) -> str:
    payload = {
        "batch_id": batch_id,
        "policy": {
            "max_selected": policy.max_selected,
            "max_selected_per_group": policy.max_selected_per_group,
            "minimum_priority_score": str(policy.minimum_priority_score),
        },
        "items": [
            {
                "opportunity_id": item.opportunity_id,
                "priority_score": str(item.priority_score),
                "priority_tier": item.priority_tier,
                "comparability_status": item.comparability_status,
                "group_key": item.group_key,
                "duplicate_key": item.duplicate_key,
                "factor_scores": {key: str(value) for key, value in item.factor_scores.items()},
                "penalties": {key: str(value) for key, value in item.penalties.items()},
                "portfolio_context": {
                    key: str(value) for key, value in item.portfolio_context.items()
                },
            }
            for item in sorted(items, key=lambda value: value.opportunity_id)
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def run_portfolio_ranking(
    batch_id: str,
    items: Iterable[PortfolioRankingItem],
    policy: CompetitionPolicy,
) -> PortfolioRankingBatchResult:
    """Validate and resolve one complete portfolio-ranking batch atomically."""
    if not batch_id.strip():
        raise ValueError("batch_id must not be blank")
    materialized = tuple(items)
    if not materialized:
        raise ValueError("ranking batch must contain at least one item")
    identifiers = [item.opportunity_id for item in materialized]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("opportunity_id values must be unique within a batch")

    by_id = {item.opportunity_id: item for item in materialized}
    candidates = tuple(
        CompetitionCandidate(
            opportunity_id=item.opportunity_id,
            priority_score=item.priority_score,
            priority_tier=item.priority_tier,
            comparability_status=item.comparability_status,
            group_key=item.group_key,
            duplicate_key=item.duplicate_key,
        )
        for item in materialized
    )
    outcomes = resolve_competition(candidates, policy)
    explanations = tuple(
        build_ranking_explanation(
            outcome,
            by_id[outcome.opportunity_id].factor_scores,
            penalties=by_id[outcome.opportunity_id].penalties,
            portfolio_context=by_id[outcome.opportunity_id].portfolio_context,
        )
        for outcome in outcomes
    )

    artifacts: list[RankingArtifact] = []
    sequence = 1
    for outcome, explanation in zip(outcomes, explanations, strict=True):
        item = by_id[outcome.opportunity_id]
        stages = (
            ("COMPARABILITY", {"status": item.comparability_status}),
            ("PORTFOLIO_CONTEXT", dict(item.portfolio_context)),
            ("FACTORS", dict(item.factor_scores)),
            (
                "PRIORITY",
                {
                    "score": str(item.priority_score),
                    "tier": item.priority_tier,
                    "penalties": dict(item.penalties),
                },
            ),
            (
                "COMPETITION",
                {
                    "rank": outcome.rank,
                    "disposition": outcome.disposition.value,
                    "reason_code": outcome.reason_code.value,
                    "competed_with": outcome.competed_with,
                },
            ),
            ("EXPLANATION", {"headline": explanation.headline, "summary": explanation.summary}),
        )
        for stage, evidence in stages:
            artifacts.append(
                RankingArtifact(item.opportunity_id, stage, sequence, _freeze(evidence))
            )
            sequence += 1

    return PortfolioRankingBatchResult(
        batch_id=batch_id,
        batch_fingerprint=_fingerprint(batch_id, materialized, policy),
        outcomes=outcomes,
        explanations=explanations,
        artifacts=tuple(artifacts),
    )
