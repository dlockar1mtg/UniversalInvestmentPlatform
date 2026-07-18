from datetime import datetime, timedelta, timezone

import pytest

from foundation.intelligence.orchestration import (
    CapitalInput, FailureScope, OrchestrationOpportunity, OrchestrationPolicyBundle,
    OrchestrationRunStatus, OrchestrationStage, PortfolioPositionSnapshot,
    PortfolioSnapshot, QuarantinedOpportunity, StageRecord, StageStatus,
    UniversalOrchestrationResult, UniversalRunRequest,
)


NOW = datetime(2026, 7, 18, tzinfo=timezone.utc)


def snapshot():
    return PortfolioSnapshot(
        "portfolio-1", NOW,
        (PortfolioPositionSnapshot("BTC", "crypto", "crypto", 1000, "0.01"),),
    )


def policy(**kwargs):
    return OrchestrationPolicyBundle(
        "5.4.1", ranking_policy=kwargs or {"maximum_selected": 4},
        allocation_policy={"reserve": 500},
    )


def opportunity(name="BTC"):
    return OrchestrationOpportunity(name, f"decision-{name}", "crypto", "crypto")


def test_portfolio_and_capital_contracts_calculate_totals():
    assert snapshot().total_market_value == 1000
    capital = CapitalInput(3000, 500, 100)
    assert capital.initially_deployable_capital == 2400
    with pytest.raises(ValueError):
        CapitalInput(100, 80, 30)


def test_policy_fingerprint_is_order_invariant_and_change_sensitive():
    first = policy(a=1, b={"x": 2, "y": 3})
    second = policy(b={"y": 3, "x": 2}, a=1)
    changed = policy(a=2, b={"x": 2, "y": 3})
    assert first.fingerprint == second.fingerprint
    assert first.fingerprint != changed.fingerprint
    assert len(first.fingerprint) == 64


def test_run_request_enforces_unique_ids_and_currency_alignment():
    request = UniversalRunRequest(
        "run-1", NOW, "decision-batch-1", snapshot(), CapitalInput(3000),
        (opportunity(),), policy(),
    )
    assert request.policies.fingerprint
    with pytest.raises(ValueError):
        UniversalRunRequest(
            "run-2", NOW, "decision-batch-1", snapshot(), CapitalInput(3000),
            (opportunity(), opportunity()), policy(),
        )


def test_stage_record_validates_counts_and_timestamps():
    record = StageRecord(
        OrchestrationStage.RANKING, StageStatus.PASSED, NOW,
        NOW + timedelta(seconds=1), 4, 0,
    )
    assert record.processed_count == 4
    with pytest.raises(ValueError):
        StageRecord(OrchestrationStage.RANKING, StageStatus.FAILED, NOW, NOW, 1, 2)


def test_completed_with_quarantine_requires_consistent_evidence():
    quarantine = QuarantinedOpportunity(
        "BAD", OrchestrationStage.DECISION, "INVALID", "Invalid decision payload",
        FailureScope.OPPORTUNITY,
    )
    result = UniversalOrchestrationResult(
        "run-1", OrchestrationRunStatus.COMPLETED_WITH_QUARANTINE,
        policy().fingerprint, (), ("BTC",), (quarantine,), "output-hash",
    )
    assert result.quarantined[0].opportunity_id == "BAD"
    with pytest.raises(ValueError):
        UniversalOrchestrationResult(
            "run-1", OrchestrationRunStatus.COMPLETED,
            policy().fingerprint, (), ("BTC",), (quarantine,), "output-hash",
        )


def test_nested_policy_and_payload_mappings_are_immutable():
    bundle = policy(nested={"values": [1, 2]})
    item = OrchestrationOpportunity(
        "BTC", "decision-BTC", "crypto", "crypto", source_payload={"x": {"y": 1}}
    )
    with pytest.raises(TypeError):
        bundle.ranking_policy["nested"]["new"] = 1
    with pytest.raises(TypeError):
        item.source_payload["x"]["y"] = 2
