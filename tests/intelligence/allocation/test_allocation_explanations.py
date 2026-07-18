from datetime import date, datetime, timezone

import pytest

from foundation.intelligence.allocation import (
    AllocationBounds, AllocationRequest, CapitalPool, CapitalPoolType,
)
from foundation.intelligence.allocation.constraints import evaluate_allocation_constraints
from foundation.intelligence.allocation.execution import build_execution_plan
from foundation.intelligence.allocation.explanations import (
    AllocationAuditInput, build_allocation_explanation_audit,
)
from foundation.intelligence.allocation.objectives import ObjectiveInputs, calculate_allocation_objective
from foundation.intelligence.allocation.optimizer import OptimizationCandidate, optimize_capital
from foundation.intelligence.allocation.sizing import SizingInputs, size_opportunity
from foundation.intelligence.allocation.supply import calculate_capital_supply


def prepared(capital=500):
    supply = calculate_capital_supply(CapitalPool("monthly", CapitalPoolType.RECURRING, capital))
    request = AllocationRequest(
        "req-BTC", "BTC", "rank-1", 90, "P1", AllocationBounds(100, 400, 700),
        "crypto", "crypto",
    )
    sizing = size_opportunity(SizingInputs(request, 80, 70, 700, 700, 700, 100), supply)
    constraints = evaluate_allocation_constraints(request, sizing, supply, [])
    objective = calculate_allocation_objective(ObjectiveInputs(request, sizing, constraints, 85, 75, 90, 80))
    optimization = optimize_capital(
        "allocation-1", "rank-1", supply,
        [OptimizationCandidate(request, constraints, objective)],
        created_at=datetime(2026, 7, 18, tzinfo=timezone.utc),
    )
    execution = build_execution_plan("plan-1", optimization, date(2026, 7, 18))
    return AllocationAuditInput(request, sizing, constraints, objective), optimization, execution


def test_builds_funded_explanation_and_six_stage_artifacts():
    audit_input, optimization, execution = prepared()
    result = build_allocation_explanation_audit([audit_input], optimization, execution)
    assert "target funded" in result.explanations[0].headline.lower()
    assert len(result.explanations[0].driver_statements) == 3
    assert [artifact.stage for artifact in result.artifacts] == [
        "REQUEST", "SIZING", "CONSTRAINTS", "OBJECTIVE", "OPTIMIZATION", "EXECUTION"
    ]


def test_batch_evidence_proves_capital_and_execution_conservation():
    audit_input, optimization, execution = prepared()
    result = build_allocation_explanation_audit([audit_input], optimization, execution)
    assert result.batch_evidence["capital_conserved"] is True
    assert result.batch_evidence["allocated_capital"] == result.batch_evidence["execution_purchase_total"]


def test_explanation_preserves_unmet_capacity_and_no_binding_constraints():
    audit_input, optimization, execution = prepared(200)
    result = build_allocation_explanation_audit([audit_input], optimization, execution)
    explanation = result.explanations[0]
    assert "unmet maximum capacity" in explanation.allocation_statement
    assert explanation.constraint_statements == ("No binding allocation constraints.",)


def test_evidence_is_immutable():
    audit_input, optimization, execution = prepared()
    result = build_allocation_explanation_audit([audit_input], optimization, execution)
    with pytest.raises(TypeError):
        result.batch_evidence["capital_conserved"] = False
    with pytest.raises(TypeError):
        result.explanations[0].audit_evidence["allocated_amount"] = "0"


def test_result_is_deterministic_for_same_inputs():
    audit_input, optimization, execution = prepared()
    first = build_allocation_explanation_audit([audit_input], optimization, execution)
    second = build_allocation_explanation_audit([audit_input], optimization, execution)
    assert first == second
    assert [artifact.sequence for artifact in first.artifacts] == list(range(1, 7))


def test_rejects_missing_inputs_and_invalid_driver_limit():
    audit_input, optimization, execution = prepared()
    with pytest.raises(ValueError):
        build_allocation_explanation_audit([], optimization, execution)
    with pytest.raises(ValueError):
        build_allocation_explanation_audit([audit_input], optimization, execution, max_drivers=0)
