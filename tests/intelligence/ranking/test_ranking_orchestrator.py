import pytest

from foundation.intelligence.ranking.competition import CompetitionPolicy
from foundation.intelligence.ranking.orchestrator import (
    PortfolioRankingItem,
    run_portfolio_ranking,
)


def item(name, score, **kwargs):
    return PortfolioRankingItem(
        name,
        score,
        kwargs.pop("priority_tier", "P1"),
        kwargs.pop("factor_scores", {"confidence": score}),
        **kwargs,
    )


def test_orchestrates_stable_ranking_explanations_and_artifacts():
    result = run_portfolio_ranking(
        "batch-1",
        [item("C", 70), item("A", 90), item("B", 80)],
        CompetitionPolicy(max_selected=2),
    )
    assert [value.opportunity_id for value in result.outcomes] == ["A", "B", "C"]
    assert len(result.explanations) == 3
    assert len(result.artifacts) == 18
    assert [value.sequence for value in result.artifacts] == list(range(1, 19))
    assert len(result.selected) == 2


def test_input_permutation_has_same_fingerprint_and_result():
    items = [item("A", 90), item("B", 80)]
    policy = CompetitionPolicy(max_selected=1)
    first = run_portfolio_ranking("batch-1", items, policy)
    second = run_portfolio_ranking("batch-1", reversed(items), policy)
    assert first.batch_fingerprint == second.batch_fingerprint
    assert first.outcomes == second.outcomes
    assert first.explanations == second.explanations


def test_fingerprint_changes_with_policy_or_evidence():
    original = run_portfolio_ranking("batch-1", [item("A", 90)], CompetitionPolicy(1))
    changed = run_portfolio_ranking("batch-1", [item("A", 91)], CompetitionPolicy(1))
    assert original.batch_fingerprint != changed.batch_fingerprint


def test_preserves_every_intermediate_stage():
    result = run_portfolio_ranking(
        "batch-1",
        [item("A", 90, portfolio_context={"target_gap": 0.2}, penalties={"risk": 3})],
        CompetitionPolicy(1),
    )
    assert [artifact.stage for artifact in result.artifacts] == [
        "COMPARABILITY", "PORTFOLIO_CONTEXT", "FACTORS", "PRIORITY", "COMPETITION", "EXPLANATION"
    ]


def test_rejects_batch_before_partial_processing():
    policy = CompetitionPolicy(1)
    with pytest.raises(ValueError):
        run_portfolio_ranking("", [item("A", 90)], policy)
    with pytest.raises(ValueError):
        run_portfolio_ranking("batch-1", [], policy)
    with pytest.raises(ValueError):
        run_portfolio_ranking("batch-1", [item("A", 90), item("A", 80)], policy)


def test_normalized_item_evidence_is_immutable():
    normalized = item("A", 90)
    with pytest.raises(TypeError):
        normalized.factor_scores["confidence"] = 0
