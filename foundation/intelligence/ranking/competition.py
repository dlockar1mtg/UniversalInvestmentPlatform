"""Deterministic competition, suppression, and deferral rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Iterable, Mapping


class CompetitionDisposition(str, Enum):
    SELECTED = "SELECTED"
    DEFERRED = "DEFERRED"
    SUPPRESSED = "SUPPRESSED"
    EXCLUDED = "EXCLUDED"


class CompetitionReasonCode(str, Enum):
    SELECTED_WITHIN_CAPACITY = "SELECTED_WITHIN_CAPACITY"
    BATCH_CAPACITY_REACHED = "BATCH_CAPACITY_REACHED"
    GROUP_CAPACITY_REACHED = "GROUP_CAPACITY_REACHED"
    BELOW_PRIORITY_FLOOR = "BELOW_PRIORITY_FLOOR"
    DUPLICATE_COMPETITION_LOSS = "DUPLICATE_COMPETITION_LOSS"
    NOT_COMPARABLE = "NOT_COMPARABLE"


@dataclass(frozen=True)
class CompetitionCandidate:
    opportunity_id: str
    priority_score: Decimal | float | int
    priority_tier: str
    comparability_status: str = "COMPARABLE"
    group_key: str = "UNGROUPED"
    duplicate_key: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.opportunity_id.strip():
            raise ValueError("opportunity_id must not be blank")
        object.__setattr__(self, "priority_score", Decimal(str(self.priority_score)))


@dataclass(frozen=True)
class CompetitionPolicy:
    max_selected: int
    max_selected_per_group: int | None = None
    minimum_priority_score: Decimal | float | int = Decimal("0")

    def __post_init__(self) -> None:
        if self.max_selected < 0:
            raise ValueError("max_selected must be non-negative")
        if self.max_selected_per_group is not None and self.max_selected_per_group < 1:
            raise ValueError("max_selected_per_group must be positive when supplied")
        object.__setattr__(
            self, "minimum_priority_score", Decimal(str(self.minimum_priority_score))
        )


@dataclass(frozen=True)
class CompetitionOutcome:
    opportunity_id: str
    disposition: CompetitionDisposition
    reason_code: CompetitionReasonCode
    priority_score: Decimal
    rank: int
    competed_with: str | None = None
    evidence: Mapping[str, object] = field(default_factory=dict)


def resolve_competition(
    candidates: Iterable[CompetitionCandidate],
    policy: CompetitionPolicy,
) -> tuple[CompetitionOutcome, ...]:
    """Resolve a batch without changing its scores or input candidates.

    Ordering is stable across input permutations: descending priority score,
    ascending priority tier text, then ascending opportunity id.
    """
    items = tuple(candidates)
    ids = [item.opportunity_id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("opportunity_id values must be unique within a batch")

    ordered = sorted(
        items,
        key=lambda item: (-item.priority_score, item.priority_tier, item.opportunity_id),
    )
    selected_count = 0
    selected_by_group: dict[str, int] = {}
    duplicate_winners: dict[str, str] = {}
    outcomes: list[CompetitionOutcome] = []

    for rank, item in enumerate(ordered, start=1):
        evidence = {
            "priority_tier": item.priority_tier,
            "group_key": item.group_key,
            "comparability_status": item.comparability_status,
            "max_selected": policy.max_selected,
            "max_selected_per_group": policy.max_selected_per_group,
        }
        status = item.comparability_status.upper()
        if status == "EXCLUDED":
            disposition = CompetitionDisposition.EXCLUDED
            reason = CompetitionReasonCode.NOT_COMPARABLE
            winner = None
        elif item.duplicate_key and item.duplicate_key in duplicate_winners:
            disposition = CompetitionDisposition.SUPPRESSED
            reason = CompetitionReasonCode.DUPLICATE_COMPETITION_LOSS
            winner = duplicate_winners[item.duplicate_key]
        elif item.priority_score < policy.minimum_priority_score:
            disposition = CompetitionDisposition.DEFERRED
            reason = CompetitionReasonCode.BELOW_PRIORITY_FLOOR
            winner = None
        elif selected_count >= policy.max_selected:
            disposition = CompetitionDisposition.DEFERRED
            reason = CompetitionReasonCode.BATCH_CAPACITY_REACHED
            winner = None
        elif (
            policy.max_selected_per_group is not None
            and selected_by_group.get(item.group_key, 0)
            >= policy.max_selected_per_group
        ):
            disposition = CompetitionDisposition.DEFERRED
            reason = CompetitionReasonCode.GROUP_CAPACITY_REACHED
            winner = None
        else:
            disposition = CompetitionDisposition.SELECTED
            reason = CompetitionReasonCode.SELECTED_WITHIN_CAPACITY
            winner = None
            selected_count += 1
            selected_by_group[item.group_key] = selected_by_group.get(item.group_key, 0) + 1
            if item.duplicate_key:
                duplicate_winners[item.duplicate_key] = item.opportunity_id

        outcomes.append(
            CompetitionOutcome(
                opportunity_id=item.opportunity_id,
                disposition=disposition,
                reason_code=reason,
                priority_score=item.priority_score,
                rank=rank,
                competed_with=winner,
                evidence=evidence,
            )
        )

    return tuple(outcomes)
