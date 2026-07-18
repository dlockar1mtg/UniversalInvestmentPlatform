from datetime import datetime, timezone

import pytest

from foundation.intelligence.orchestration import (
    CapitalInput,
    InMemoryRunRegistry,
    OrchestrationEnginePolicy,
    OrchestrationOpportunity,
    OrchestrationPolicyBundle,
    OrchestrationRunStatus,
    PortfolioSnapshot,
    RecoveryAction,
    UniversalRunRequest,
    request_fingerprint,
)
from foundation.intelligence.ranking.competition import CompetitionPolicy


NOW = datetime(2026, 7, 18, 12, tzinfo=timezone.utc)


def opportunity(identifier="opp-1", score="82"):
    return OrchestrationOpportunity(
        identifier, f"decision-{identifier}", "ETF", "equities",
        source_payload={
            "priority_score": score,
            "priority_tier": "HIGH",
            "factor_scores": {"confidence": "80"},
            "allocation_bounds": {
                "minimum_amount": "100", "target_amount": "500", "maximum_amount": "900",
            },
            "sizing_inputs": {
                "confidence_score": "80", "action_strength_score": "75",
                "portfolio_gap_amount": "1000", "opportunity_capacity_amount": "900",
                "liquidity_capacity_amount": "800",
            },
            "objective_inputs": {
                "target_gap_score": "80", "diversification_score": "70",
                "liquidity_score": "75", "capital_efficiency_score": "85",
            },
        },
    )


def request(items, *, run_id="run-1", gross="2000"):
    return UniversalRunRequest(
        run_id, NOW, "decision-batch-1", PortfolioSnapshot("portfolio-1", NOW, ()),
        CapitalInput(gross, "200", "100"), tuple(items),
        OrchestrationPolicyBundle("policy-1"),
    )


POLICY = OrchestrationEnginePolicy(CompetitionPolicy(max_selected=10))


def test_request_fingerprint_is_order_invariant_and_change_sensitive():
    first = request((opportunity("b"), opportunity("a")))
    reversed_request = request((opportunity("a"), opportunity("b")))
    changed = request((opportunity("a"), opportunity("b")), gross="2100")
    assert request_fingerprint(first) == request_fingerprint(reversed_request)
    assert request_fingerprint(first) != request_fingerprint(changed)


def test_registration_is_idempotent_and_rejects_run_id_input_conflicts():
    registry = InMemoryRunRegistry()
    original = request((opportunity(),))
    assert registry.register(original) == registry.register(original)
    with pytest.raises(ValueError, match="different immutable inputs"):
        registry.register(request((opportunity(),), gross="2100"))


def test_execute_records_attempt_and_reuses_completed_result_idempotently():
    registry = InMemoryRunRegistry()
    original = request((opportunity(),))
    first = registry.execute(original, POLICY)
    second = registry.execute(original, POLICY)
    assert first is second
    assert len(registry.get("run-1").attempts) == 1
    assert registry.recovery_plan("run-1").action is RecoveryAction.RETURN_COMPLETED


def test_reproducibility_verification_records_matching_attempt():
    registry = InMemoryRunRegistry()
    registry.execute(request((opportunity(),)), POLICY)
    report = registry.verify_reproducibility("run-1", POLICY)
    assert report.reproducible
    assert report.reference_attempt == 1 and report.replay_attempt == 2
    assert len(registry.get("run-1").attempts) == 2


def test_failed_run_recovery_replays_from_atomic_start_with_history():
    registry = InMemoryRunRegistry()
    invalid = request((opportunity(score="101"),))
    failed = registry.execute(invalid, POLICY)
    assert failed.run.status is OrchestrationRunStatus.FAILED
    plan = registry.recovery_plan("run-1")
    assert plan.action is RecoveryAction.REPLAY_FROM_ATOMIC_START
    assert plan.last_passed_stage.value == "DECISION"
    recovered = registry.recover("run-1", POLICY)
    assert recovered.run.status is OrchestrationRunStatus.FAILED
    assert len(registry.get("run-1").attempts) == 2


def test_registry_listing_and_unknown_run_behavior_are_deterministic():
    registry = InMemoryRunRegistry()
    registry.register(request((opportunity("b"),), run_id="run-b"))
    registry.register(request((opportunity("a"),), run_id="run-a"))
    assert tuple(item.run_id for item in registry.list_runs()) == ("run-a", "run-b")
    with pytest.raises(KeyError, match="unknown orchestration run"):
        registry.get("missing")
