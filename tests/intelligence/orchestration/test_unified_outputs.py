from dataclasses import replace
from datetime import datetime, timezone
import csv
import io
import json

import pytest

from foundation.intelligence.orchestration import (
    CapitalInput, OrchestrationEnginePolicy, OrchestrationOpportunity,
    OrchestrationPolicyBundle, OrchestrationRunStatus, PortfolioSnapshot,
    UniversalRunRequest, build_unified_output, run_universal_orchestration,
    validate_unified_output,
)
from foundation.intelligence.ranking.competition import CompetitionPolicy


NOW = datetime(2026, 7, 18, 12, tzinfo=timezone.utc)


def opportunity(identifier="opp-1", score="82", *, valid=True):
    payload = {
        "priority_score": score, "priority_tier": "HIGH",
        "factor_scores": {"confidence": "80", "capacity": "75"},
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
    }
    if not valid:
        payload.pop("sizing_inputs")
    return OrchestrationOpportunity(
        identifier, f"decision-{identifier}", "ETF", "equities", source_payload=payload
    )


def execute(*items):
    request = UniversalRunRequest(
        "run-1", NOW, "decision-batch-1", PortfolioSnapshot("portfolio-1", NOW, ()),
        CapitalInput("2000", "200", "100"), tuple(items),
        OrchestrationPolicyBundle("policy-1"),
    )
    return run_universal_orchestration(
        request, OrchestrationEnginePolicy(CompetitionPolicy(max_selected=10))
    )


def test_complete_package_joins_ranking_allocation_execution_and_capital():
    package = build_unified_output(execute(opportunity()))
    document = json.loads(package.json_text)
    row = package.dashboard_rows[0]
    assert document["run_status"] == "COMPLETED"
    assert document["capital_summary"]["capital_conserved"] is True
    assert row["ranking_disposition"] == "SELECTED"
    assert row["allocation_status"] in {"ALLOCATED", "PARTIALLY_ALLOCATED"}
    assert row["execution_amount"] == row["allocated_amount"]


def test_dashboard_and_audit_csv_preserve_cardinality_and_order():
    package = build_unified_output(execute(opportunity("b", "75"), opportunity("a", "90")))
    dashboard = tuple(csv.DictReader(io.StringIO(package.dashboard_csv)))
    audit = tuple(csv.DictReader(io.StringIO(package.audit_csv)))
    assert tuple(row["opportunity_id"] for row in dashboard) == ("a", "b")
    assert len(audit) == len(package.audit_rows)
    assert tuple(int(row["sequence"]) for row in audit) == tuple(range(1, len(audit) + 1))


def test_quarantine_is_visible_in_explanation_dashboard_and_audit():
    package = build_unified_output(execute(opportunity("good"), opportunity("bad", valid=False)))
    by_id = {row["opportunity_id"]: row for row in package.dashboard_rows}
    assert package.run_status == OrchestrationRunStatus.COMPLETED_WITH_QUARANTINE.value
    assert by_id["bad"]["quarantine_stage"] == "SIZING"
    assert "quarantined" in by_id["bad"]["headline"]
    assert any(row["stage"] == "QUARANTINE_SIZING" for row in package.audit_rows)


def test_failed_run_still_produces_machine_readable_outputs():
    package = build_unified_output(execute(opportunity(score="101")))
    document = json.loads(package.json_text)
    assert package.run_status == "FAILED"
    assert document["ranking_batch_id"] is None
    assert document["capital_summary"] is None
    assert package.dashboard_rows[0]["quarantine_reason"]


def test_output_is_deterministic_across_input_order_and_compact_json_modes():
    first = build_unified_output(execute(opportunity("b", "75"), opportunity("a", "90")), indent=None)
    second = build_unified_output(execute(opportunity("a", "90"), opportunity("b", "75")), indent=None)
    assert first.package_fingerprint == second.package_fingerprint
    assert first.json_text == second.json_text
    assert first.dashboard_csv == second.dashboard_csv
    assert first.audit_csv == second.audit_csv


def test_integrity_validation_passes_and_detects_tampering():
    package = build_unified_output(execute(opportunity()))
    validate_unified_output(package)
    tampered = replace(package, json_text=package.json_text.replace("COMPLETED", "CORRUPTED", 1))
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        validate_unified_output(tampered)
