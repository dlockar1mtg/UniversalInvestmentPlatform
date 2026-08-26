from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = json.loads(
    (ROOT / "config" / "metals" / "bounded_realized_return_derivation_execution_authorization.json").read_text(encoding="utf-8")
)


def test_identity_and_source_bindings():
    assert AUTH["authorization_id"] == "METALS-BOUNDED-REALIZED-RETURN-DERIVATION-EXECUTION-AUTHORIZATION-1"
    assert AUTH["source_design_id"] == "METALS-BOUNDED-REALIZED-RETURN-DERIVATION-DESIGN-1"
    assert AUTH["source_design_head"] == "6d61723d19fb781cfe3fc13d5dc0c9702e3e0d3a"
    assert AUTH["source_readiness_audit_id"] == "METALS-FINAL-DECISION-HISTORICAL-VALIDATION-READINESS-RECOVERY-AUDIT-1"


def test_certified_readiness_findings_are_bound():
    findings = AUTH["certified_readiness_findings"]
    assert findings["readiness_finding"] == "READY_AFTER_REALIZED_RETURN_DERIVATION"
    assert findings["historical_surface_count"] == 61
    assert findings["joinability_row_count"] == 48
    assert findings["joinable_asset_horizon_row_count"] == 48
    assert findings["history_join_recovery_row_count"] == 0
    assert findings["certified_price_history_present"] is True
    assert findings["existing_realized_outcome_present"] is False
    assert findings["realized_return_derivation_required"] is True
    assert findings["consumed_holdout_evidence_present"] is True


def test_required_execution_behavior_is_exact_and_true():
    behavior = AUTH["required_execution_behavior"]
    assert len(behavior) == 16
    assert all(value is True for value in behavior.values())
    assert behavior["derive_realized_returns_from_certified_unadjusted_price_history_only"] is True
    assert behavior["use_first_governed_observation_at_or_after_target_horizon_date"] is True
    assert behavior["preserve_consumed_holdouts_without_reuse"] is True
    assert behavior["do_not_consume_new_holdout"] is True


def test_required_outputs_are_exact_and_true():
    outputs = AUTH["required_outputs"]
    expected = {
        "realized_return_rows_csv",
        "realized_return_rows_json",
        "derivation_lineage_json",
        "coverage_summary_json",
        "missing_future_price_register_json",
        "consumed_interval_annotation_json",
        "derivation_summary_json",
    }
    assert set(outputs) == expected
    assert len(outputs) == 7
    assert all(value is True for value in outputs.values())


def test_authorization_boundary_is_fail_closed():
    boundary = AUTH["authorization_boundary"]
    assert boundary["bounded_realized_return_derivation_authorized"] is True
    assert boundary["local_evidence_artifact_write_authorized"] is True
    for key, value in boundary.items():
        if key in {
            "bounded_realized_return_derivation_authorized",
            "local_evidence_artifact_write_authorized",
        }:
            continue
        assert value is False, key


def test_decisions_are_bound():
    assert AUTH["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_REALIZED_RETURN_DERIVATION"
    assert AUTH["next_decision"] == "EXECUTE_AND_CERTIFY_BOUNDED_METALS_REALIZED_RETURN_DERIVATION"
