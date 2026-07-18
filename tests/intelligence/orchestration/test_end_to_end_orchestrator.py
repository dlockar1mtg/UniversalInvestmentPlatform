from datetime import datetime, timezone
from decimal import Decimal

from foundation.intelligence.orchestration import (
    CapitalInput,
    OrchestrationEnginePolicy,
    OrchestrationOpportunity,
    OrchestrationPolicyBundle,
    OrchestrationRunStatus,
    OrchestrationStage,
    PortfolioSnapshot,
    UniversalRunRequest,
    run_universal_orchestration,
)
from foundation.intelligence.ranking.competition import CompetitionPolicy


NOW = datetime(2026, 7, 18, 12, tzinfo=timezone.utc)


def opportunity(identifier="opp-1", score="82", *, valid=True):
    payload = {
        "priority_score": score,
        "priority_tier": "HIGH",
        "factor_scores": {"confidence": "80", "capacity": "75"},
        "allocation_bounds": {
            "minimum_amount": "100", "target_amount": "500", "maximum_amount": "900",
        },
        "sizing_inputs": {
            "confidence_score": "80", "action_strength_score": "75",
            "portfolio_gap_amount": "1000", "opportunity_capacity_amount": "900",
            "liquidity_capacity_amount": "800", "minimum_purchase_amount": "100",
        },
        "objective_inputs": {
            "target_gap_score": "80", "diversification_score": "70",
            "liquidity_score": "75", "capital_efficiency_score": "85",
        },
    }
    if not valid:
        payload.pop("sizing_inputs")
    return OrchestrationOpportunity(
        identifier, f"decision-{identifier}", "ETF", "equities", source_payload=payload
    )


def request(*items):
    return UniversalRunRequest(
        "run-1", NOW, "decision-batch-1",
        PortfolioSnapshot("portfolio-1", NOW, ()),
        CapitalInput("2000", "200", "100"),
        tuple(items),
        OrchestrationPolicyBundle("policy-1", ranking_policy={"max_selected": 10}),
    )


def policy(max_selected=10):
    return OrchestrationEnginePolicy(CompetitionPolicy(max_selected=max_selected))


def test_complete_run_executes_all_stages_and_conserves_capital():
    result = run_universal_orchestration(request(opportunity()), policy())
    assert result.run.status is OrchestrationRunStatus.COMPLETED
    assert tuple(record.stage for record in result.run.stage_records) == (
        OrchestrationStage.DECISION, OrchestrationStage.RANKING,
        OrchestrationStage.CAPITAL_SUPPLY, OrchestrationStage.SIZING,
        OrchestrationStage.CONSTRAINTS, OrchestrationStage.OBJECTIVES,
        OrchestrationStage.OPTIMIZATION, OrchestrationStage.EXECUTION,
    )
    capital = result.optimization.capital_result
    assert capital.gross_capital == capital.reserved_capital + capital.allocated_capital + capital.residual_capital
    assert result.execution_plan.purchase_total == capital.allocated_capital


def test_run_is_deterministic_and_input_order_invariant():
    first = run_universal_orchestration(
        request(opportunity("b", "75"), opportunity("a", "90")), policy()
    )
    second = run_universal_orchestration(
        request(opportunity("a", "90"), opportunity("b", "75")), policy()
    )
    assert first.run.output_fingerprint == second.run.output_fingerprint
    assert first.optimization.allocation_order == second.optimization.allocation_order


def test_invalid_opportunity_is_quarantined_while_valid_one_completes():
    result = run_universal_orchestration(
        request(opportunity("good"), opportunity("bad", valid=False)), policy()
    )
    assert result.run.status is OrchestrationRunStatus.COMPLETED_WITH_QUARANTINE
    assert result.run.successful_opportunity_ids == ("good",)
    assert result.run.quarantined[0].opportunity_id == "bad"
    assert result.run.quarantined[0].stage is OrchestrationStage.SIZING


def test_ranking_capacity_only_hands_selected_items_to_allocation():
    result = run_universal_orchestration(
        request(opportunity("lower", "60"), opportunity("higher", "90")), policy(1)
    )
    assert tuple(item.opportunity_id for item in result.sizing_results) == ("higher",)
    assert result.run.successful_opportunity_ids == ("higher",)


def test_all_invalid_decision_handoffs_return_failed_batch_evidence():
    item = opportunity(score="101")
    result = run_universal_orchestration(request(item), policy())
    assert result.run.status is OrchestrationRunStatus.FAILED
    assert result.ranking is None
    assert result.run.stage_records[-1].status.value == "FAILED"
    assert result.run.quarantined[0].opportunity_id == "opp-1"


def test_policy_fingerprint_and_source_lineage_are_preserved():
    source = opportunity()
    run_request = request(source)
    result = run_universal_orchestration(run_request, policy())
    allocation_request = result.optimization.capital_result.lines[0]
    assert result.run.policy_fingerprint == run_request.policies.fingerprint
    assert result.ranking.batch_id == "run-1:ranking"
    assert allocation_request.request_id == "run-1:ranking:opp-1"
    assert result.run.output_fingerprint and len(result.run.output_fingerprint) == 64
