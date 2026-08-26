from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "config" / "metals" / "bounded_realized_return_derivation_design.json"


def load_design():
    return json.loads(DESIGN.read_text(encoding="utf-8"))


def test_identity_and_source_bindings():
    d = load_design()
    assert d["design_id"] == "METALS-BOUNDED-REALIZED-RETURN-DERIVATION-DESIGN-1"
    assert d["source_governed_head"] == "0baa85e6c1a7ade3f9f8d7ea7c880e51e6a7552b"
    assert d["source_readiness_audit_id"] == "METALS-FINAL-DECISION-HISTORICAL-VALIDATION-READINESS-RECOVERY-AUDIT-1"
    assert d["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def test_certified_readiness_is_bound():
    f = load_design()["certified_readiness_findings"]
    assert f["readiness_finding"] == "READY_AFTER_REALIZED_RETURN_DERIVATION"
    assert f["historical_surface_count"] == 61
    assert f["historical_recommendation_present"] is True
    assert f["historical_forecast_present"] is True
    assert f["historical_adjusted_view_present"] is True
    assert f["certified_price_history_present"] is True
    assert f["existing_realized_outcome_present"] is False
    assert f["joinability_row_count"] == 48
    assert f["joinable_asset_horizon_row_count"] == 48
    assert f["history_join_recovery_row_count"] == 0
    assert f["realized_return_derivation_required"] is True
    assert f["consumed_holdout_evidence_present"] is True


def test_derivation_method_is_strict():
    d = load_design()
    assert len(d["required_method"]) == 12
    assert all(value is True for value in d["required_method"].values())
    assert d["required_scope"]["target_horizons_months"] == [3, 6, 12, 24]
    assert d["required_scope"]["expected_joinability_rows"] == 48
    assert d["required_scope"]["reference_control_assets"] == ["BIL"]


def test_consumed_holdout_rules_are_closed():
    d = load_design()
    assert len(d["consumed_holdout_rules"]) == 5
    assert all(value is True for value in d["consumed_holdout_rules"].values())


def test_required_outputs_are_exact():
    d = load_design()
    assert set(d["required_outputs"]) == {
        "realized_return_rows_csv",
        "realized_return_rows_json",
        "derivation_lineage_json",
        "coverage_summary_json",
        "missing_future_price_register_json",
        "consumed_interval_annotation_json",
        "derivation_summary_json",
    }
    assert all(value is True for value in d["required_outputs"].values())


def test_no_execution_is_authorized():
    d = load_design()
    assert all(value is False for value in d["boundaries"].values())


def test_decisions_are_bound():
    d = load_design()
    assert d["design_decision"] == "APPROVE_BOUNDED_METALS_REALIZED_RETURN_DERIVATION_DESIGN_FOR_EXECUTION_AUTHORIZATION_CONSIDERATION"
    assert d["next_decision"] == "AUTHORIZE_BOUNDED_METALS_REALIZED_RETURN_DERIVATION"
