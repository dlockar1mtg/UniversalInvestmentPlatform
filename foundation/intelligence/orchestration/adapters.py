"""Deterministic, auditable handoffs between Phase 5 intelligence engines."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Iterable, Mapping

from foundation.intelligence.allocation.contracts import AllocationBounds, AllocationRequest
from foundation.intelligence.ranking.orchestrator import (
    PortfolioRankingBatchResult,
    PortfolioRankingItem,
)

from .contracts import (
    OrchestrationOpportunity,
    OrchestrationStage,
    QuarantinedOpportunity,
)


def _freeze(values: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType({str(key): values[key] for key in sorted(values, key=str)})


def _mapping(value: object, name: str, *, required: bool = False) -> Mapping[str, object]:
    if value is None and not required:
        return {}
    if not isinstance(value, Mapping) or (required and not value):
        raise ValueError(f"{name} must be a non-empty mapping" if required else f"{name} must be a mapping")
    return value


def _score(value: object) -> Decimal:
    try:
        converted = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("priority_score must be numeric") from exc
    if not converted.is_finite() or converted < 0 or converted > 100:
        raise ValueError("priority_score must be between 0 and 100")
    return converted


@dataclass(frozen=True)
class AdapterEvidence:
    opportunity_id: str
    source_id: str
    source_stage: OrchestrationStage
    target_stage: OrchestrationStage
    fields_preserved: tuple[str, ...]
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.opportunity_id.strip() or not self.source_id.strip():
            raise ValueError("adapter evidence identifiers must not be blank")
        if not self.fields_preserved:
            raise ValueError("fields_preserved must not be empty")
        object.__setattr__(self, "metadata", _freeze(self.metadata))


@dataclass(frozen=True)
class DecisionRankingAdapterResult:
    items: tuple[PortfolioRankingItem, ...]
    quarantined: tuple[QuarantinedOpportunity, ...]
    evidence: tuple[AdapterEvidence, ...]


@dataclass(frozen=True)
class RankingAllocationAdapterResult:
    requests: tuple[AllocationRequest, ...]
    quarantined: tuple[QuarantinedOpportunity, ...]
    evidence: tuple[AdapterEvidence, ...]


def adapt_decisions_to_ranking(
    opportunities: Iterable[OrchestrationOpportunity],
) -> DecisionRankingAdapterResult:
    """Normalize decision handoffs without recalculating their ranking values.

    Each source payload must contain ``priority_score``, ``priority_tier``, and
    a non-empty ``factor_scores`` mapping. Optional ranking fields pass through.
    Invalid opportunities are isolated with deterministic quarantine evidence.
    """
    materialized = tuple(opportunities)
    identifiers = [item.opportunity_id for item in materialized]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("opportunity_id values must be unique at the adapter boundary")

    items: list[PortfolioRankingItem] = []
    quarantined: list[QuarantinedOpportunity] = []
    evidence: list[AdapterEvidence] = []
    for opportunity in sorted(materialized, key=lambda item: item.opportunity_id):
        payload = opportunity.source_payload
        try:
            tier = str(payload["priority_tier"])
            if not tier.strip():
                raise ValueError("priority_tier must not be blank")
            item = PortfolioRankingItem(
                opportunity_id=opportunity.opportunity_id,
                priority_score=_score(payload["priority_score"]),
                priority_tier=tier,
                factor_scores=_mapping(payload.get("factor_scores"), "factor_scores", required=True),
                comparability_status=str(payload.get("comparability_status", "COMPARABLE")),
                penalties=_mapping(payload.get("penalties"), "penalties"),
                portfolio_context=_mapping(payload.get("portfolio_context"), "portfolio_context"),
                group_key=opportunity.group_key,
                duplicate_key=(
                    str(payload["duplicate_key"]) if payload.get("duplicate_key") is not None else None
                ),
            )
        except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
            quarantined.append(
                QuarantinedOpportunity(
                    opportunity_id=opportunity.opportunity_id,
                    stage=OrchestrationStage.RANKING,
                    reason_code="INVALID_DECISION_RANKING_HANDOFF",
                    message=str(exc),
                )
            )
            continue
        items.append(item)
        evidence.append(
            AdapterEvidence(
                opportunity_id=opportunity.opportunity_id,
                source_id=opportunity.decision_id,
                source_stage=OrchestrationStage.DECISION,
                target_stage=OrchestrationStage.RANKING,
                fields_preserved=("opportunity_id", "decision_id", "group_key", "priority_score"),
                metadata={"asset_class": opportunity.asset_class, "currency": opportunity.currency},
            )
        )
    return DecisionRankingAdapterResult(tuple(items), tuple(quarantined), tuple(evidence))


def adapt_ranking_to_allocation(
    ranking: PortfolioRankingBatchResult,
    opportunities: Iterable[OrchestrationOpportunity],
) -> RankingAllocationAdapterResult:
    """Create allocation requests for selected ranking outcomes only.

    Allocation bounds are a prior sizing output supplied in each opportunity's
    ``source_payload['allocation_bounds']`` mapping. The adapter never invents
    or adjusts bounds, scores, tiers, or ranking dispositions.
    """
    materialized = tuple(opportunities)
    by_id = {item.opportunity_id: item for item in materialized}
    if len(by_id) != len(materialized):
        raise ValueError("opportunity_id values must be unique at the adapter boundary")

    requests: list[AllocationRequest] = []
    quarantined: list[QuarantinedOpportunity] = []
    evidence: list[AdapterEvidence] = []
    selected = sorted(ranking.selected, key=lambda item: (item.rank, item.opportunity_id))
    explanations = {item.opportunity_id: item for item in ranking.explanations}
    for outcome in selected:
        try:
            opportunity = by_id[outcome.opportunity_id]
            payload = opportunity.source_payload
            bounds_payload = _mapping(
                payload.get("allocation_bounds"), "allocation_bounds", required=True
            )
            bounds = AllocationBounds(
                minimum_amount=bounds_payload["minimum_amount"],
                target_amount=bounds_payload["target_amount"],
                maximum_amount=bounds_payload["maximum_amount"],
            )
            tier = str(outcome.evidence["priority_tier"])
            request = AllocationRequest(
                request_id=f"{ranking.batch_id}:{outcome.opportunity_id}",
                opportunity_id=outcome.opportunity_id,
                ranking_batch_id=ranking.batch_id,
                priority_score=outcome.priority_score,
                priority_tier=tier,
                bounds=bounds,
                asset_class=opportunity.asset_class,
                group_key=opportunity.group_key,
                currency=opportunity.currency,
                metadata={
                    "decision_id": opportunity.decision_id,
                    "ranking_fingerprint": ranking.batch_fingerprint,
                    "ranking_rank": outcome.rank,
                    "ranking_disposition": outcome.disposition.value,
                    "ranking_reason_code": outcome.reason_code.value,
                    "ranking_headline": explanations[outcome.opportunity_id].headline,
                },
            )
        except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
            quarantined.append(
                QuarantinedOpportunity(
                    opportunity_id=outcome.opportunity_id,
                    stage=OrchestrationStage.SIZING,
                    reason_code="INVALID_RANKING_ALLOCATION_HANDOFF",
                    message=str(exc),
                )
            )
            continue
        requests.append(request)
        evidence.append(
            AdapterEvidence(
                opportunity_id=outcome.opportunity_id,
                source_id=ranking.batch_id,
                source_stage=OrchestrationStage.RANKING,
                target_stage=OrchestrationStage.SIZING,
                fields_preserved=(
                    "opportunity_id", "ranking_batch_id", "priority_score",
                    "priority_tier", "allocation_bounds",
                ),
                metadata={"rank": outcome.rank, "decision_id": opportunity.decision_id},
            )
        )
    return RankingAllocationAdapterResult(tuple(requests), tuple(quarantined), tuple(evidence))
