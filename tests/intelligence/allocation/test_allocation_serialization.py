import csv
from datetime import date, datetime, timezone
import io
import json

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
from foundation.intelligence.allocation.serialization import (
    ALLOCATION_COLUMNS, AUDIT_COLUMNS, EXECUTION_COLUMNS,
    allocation_audit_csv, allocation_audit_rows, allocation_bundle_json,
    allocation_dashboard_csv, allocation_dashboard_rows,
    execution_dashboard_csv, execution_dashboard_rows,
)
from foundation.intelligence.allocation.sizing import SizingInputs, size_opportunity
from foundation.intelligence.allocation.supply import calculate_capital_supply


def outputs():
    supply = calculate_capital_supply(CapitalPool("monthly", CapitalPoolType.RECURRING, 500))
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
    plan = build_execution_plan("plan-1", optimization, date(2026, 7, 18))
    audit = build_allocation_explanation_audit(
        [AllocationAuditInput(request, sizing, constraints, objective)], optimization, plan
    )
    return optimization, plan, audit


def test_complete_json_is_valid_deterministic_and_versioned():
    optimization, plan, audit = outputs()
    first = allocation_bundle_json(optimization, plan, audit)
    second = allocation_bundle_json(optimization, plan, audit)
    assert first == second
    payload = json.loads(first)
    assert payload["schema_version"] == "5.3.9"
    assert payload["capital_summary"]["allocated_capital"] == "500.00"
    assert len(payload["audit_records"]) == 6


def test_allocation_rows_and_csv_have_fixed_columns():
    optimization, _, audit = outputs()
    rows = allocation_dashboard_rows(optimization, audit)
    assert rows[0]["opportunity_id"] == "BTC"
    assert rows[0]["allocation_status"] == "ALLOCATED"
    parsed = list(csv.DictReader(io.StringIO(allocation_dashboard_csv(optimization, audit))))
    assert tuple(parsed[0]) == ALLOCATION_COLUMNS


def test_execution_rows_preserve_sequence_dates_and_amounts():
    _, plan, _ = outputs()
    rows = execution_dashboard_rows(plan)
    assert rows[0]["sequence"] == 1
    assert rows[0]["scheduled_date"] == "2026-07-18"
    parsed = list(csv.DictReader(io.StringIO(execution_dashboard_csv(plan))))
    assert tuple(parsed[0]) == EXECUTION_COLUMNS
    assert parsed[0]["amount"] == "500.00"


def test_audit_rows_preserve_six_ordered_stages():
    _, _, audit = outputs()
    rows = allocation_audit_rows(audit)
    assert [row["sequence"] for row in rows] == list(range(1, 7))
    assert json.loads(rows[0]["evidence_json"])["priority_tier"] == "P1"
    parsed = list(csv.DictReader(io.StringIO(allocation_audit_csv(audit))))
    assert tuple(parsed[0]) == AUDIT_COLUMNS


def test_outputs_do_not_emit_python_decimal_enum_or_mapping_representations():
    optimization, plan, audit = outputs()
    combined = (
        allocation_bundle_json(optimization, plan, audit)
        + allocation_dashboard_csv(optimization, audit)
        + execution_dashboard_csv(plan)
        + allocation_audit_csv(audit)
    )
    assert "Decimal(" not in combined
    assert "AllocationStatus." not in combined
    assert "mappingproxy(" not in combined


def test_json_capital_and_execution_totals_agree():
    optimization, plan, audit = outputs()
    payload = json.loads(allocation_bundle_json(optimization, plan, audit))
    assert payload["capital_summary"]["allocated_capital"] == payload["execution_plan"]["purchase_total"]
    assert payload["capital_summary"]["residual_capital"] == payload["execution_plan"]["retained_cash"]
