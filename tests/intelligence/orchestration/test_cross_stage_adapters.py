from decimal import Decimal

import pytest

from foundation.intelligence.orchestration import (
    OrchestrationOpportunity,
    OrchestrationStage,
    adapt_decisions_to_ranking,
    adapt_ranking_to_allocation,
)
from foundation.intelligence.ranking.competition import CompetitionPolicy
from foundation.intelligence.ranking.orchestrator import run_portfolio_ranking


def opportunity(identifier="opp-1", score="82", bounds=True):
    payload = {
        "priority_score": score,
        "priority_tier": "HIGH",
        "factor_scores": {"confidence": "80", "capacity": "75"},
        "portfolio_context": {"diversification": "60"},
    }
    if bounds:
        payload["allocation_bounds"] = {
            "minimum_amount": "100", "target_amount": "500", "maximum_amount": "900"
        }
    return OrchestrationOpportunity(
        opportunity_id=identifier,
        decision_id=f"decision-{identifier}",
        asset_class="ETF",
        group_key="equities",
        source_payload=payload,
    )


def ranking_result(*items):
    adapted = adapt_decisions_to_ranking(items)
    return run_portfolio_ranking(
        "ranking-1", adapted.items, CompetitionPolicy(max_selected=10)
    )


def test_decision_to_ranking_preserves_identity_values_and_provenance():
    result = adapt_decisions_to_ranking((opportunity(),))
    assert result.items[0].opportunity_id == "opp-1"
    assert result.items[0].priority_score == Decimal("82")
    assert result.items[0].group_key == "equities"
    assert result.evidence[0].source_id == "decision-opp-1"
    assert result.quarantined == ()


def test_invalid_decision_payload_is_quarantined_without_hiding_valid_item():
    invalid = opportunity("bad", score="101")
    result = adapt_decisions_to_ranking((invalid, opportunity()))
    assert tuple(item.opportunity_id for item in result.items) == ("opp-1",)
    assert result.quarantined[0].opportunity_id == "bad"
    assert result.quarantined[0].stage is OrchestrationStage.RANKING
    assert result.quarantined[0].reason_code == "INVALID_DECISION_RANKING_HANDOFF"


def test_decision_adapter_is_input_order_invariant():
    first = adapt_decisions_to_ranking((opportunity("b"), opportunity("a")))
    second = adapt_decisions_to_ranking((opportunity("a"), opportunity("b")))
    assert first == second


def test_ranking_to_allocation_preserves_selected_rank_score_bounds_and_lineage():
    source = opportunity()
    result = adapt_ranking_to_allocation(ranking_result(source), (source,))
    request = result.requests[0]
    assert request.opportunity_id == "opp-1"
    assert request.priority_score == Decimal("82")
    assert request.bounds.target_amount == Decimal("500")
    assert request.metadata["decision_id"] == "decision-opp-1"
    assert request.metadata["ranking_rank"] == 1
    assert result.quarantined == ()


def test_missing_sizing_bounds_quarantines_selected_opportunity():
    source = opportunity(bounds=False)
    result = adapt_ranking_to_allocation(ranking_result(source), (source,))
    assert result.requests == ()
    assert result.quarantined[0].stage is OrchestrationStage.SIZING
    assert result.quarantined[0].reason_code == "INVALID_RANKING_ALLOCATION_HANDOFF"


def test_duplicate_identifiers_fail_each_adapter_boundary():
    duplicate = opportunity()
    with pytest.raises(ValueError, match="unique"):
        adapt_decisions_to_ranking((duplicate, duplicate))
    ranked = ranking_result(duplicate)
    with pytest.raises(ValueError, match="unique"):
        adapt_ranking_to_allocation(ranked, (duplicate, duplicate))
