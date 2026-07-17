from decimal import Decimal

import pytest

from foundation.intelligence.ranking.competition import (
    CompetitionCandidate,
    CompetitionDisposition,
    CompetitionPolicy,
    CompetitionReasonCode,
    resolve_competition,
)


def candidate(name, score, **kwargs):
    return CompetitionCandidate(name, score, kwargs.pop("priority_tier", "P1"), **kwargs)


def test_selects_highest_priority_with_stable_ordering():
    batch = [candidate("C", 70), candidate("A", 90), candidate("B", 80)]
    outcomes = resolve_competition(batch, CompetitionPolicy(max_selected=2))
    assert [item.opportunity_id for item in outcomes] == ["A", "B", "C"]
    assert [item.disposition for item in outcomes] == [
        CompetitionDisposition.SELECTED,
        CompetitionDisposition.SELECTED,
        CompetitionDisposition.DEFERRED,
    ]
    assert outcomes[-1].reason_code is CompetitionReasonCode.BATCH_CAPACITY_REACHED


def test_group_capacity_defers_without_consuming_batch_capacity():
    batch = [
        candidate("A", 90, group_key="crypto"),
        candidate("B", 80, group_key="crypto"),
        candidate("C", 70, group_key="metals"),
    ]
    outcomes = resolve_competition(
        batch, CompetitionPolicy(max_selected=2, max_selected_per_group=1)
    )
    assert outcomes[1].reason_code is CompetitionReasonCode.GROUP_CAPACITY_REACHED
    assert outcomes[2].disposition is CompetitionDisposition.SELECTED


def test_duplicate_loser_is_suppressed_with_winner_reference():
    outcomes = resolve_competition(
        [candidate("A", 90, duplicate_key="BTC"), candidate("B", 80, duplicate_key="BTC")],
        CompetitionPolicy(max_selected=2),
    )
    assert outcomes[1].disposition is CompetitionDisposition.SUPPRESSED
    assert outcomes[1].competed_with == "A"


def test_excluded_and_below_floor_are_auditable():
    outcomes = resolve_competition(
        [
            candidate("A", 90, comparability_status="EXCLUDED"),
            candidate("B", 40),
        ],
        CompetitionPolicy(max_selected=2, minimum_priority_score=50),
    )
    assert outcomes[0].disposition is CompetitionDisposition.EXCLUDED
    assert outcomes[1].reason_code is CompetitionReasonCode.BELOW_PRIORITY_FLOOR
    assert outcomes[1].priority_score == Decimal("40")


def test_input_permutations_produce_identical_results():
    batch = [candidate("A", 80), candidate("B", 80), candidate("C", 70)]
    policy = CompetitionPolicy(max_selected=2)
    assert resolve_competition(batch, policy) == resolve_competition(reversed(batch), policy)


def test_rejects_duplicate_ids_and_invalid_policy():
    with pytest.raises(ValueError):
        resolve_competition([candidate("A", 1), candidate("A", 2)], CompetitionPolicy(1))
    with pytest.raises(ValueError):
        CompetitionPolicy(-1)
