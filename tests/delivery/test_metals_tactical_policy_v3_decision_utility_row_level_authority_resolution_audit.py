from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config/metals/tactical_policy_v3_decision_utility_row_level_authority_resolution_audit.json"
SCRIPT = ROOT / "scripts/audit_metals_decision_utility_row_level_authority_resolution.py"


def test_config_identity_and_source_binding() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert payload["audit_id"] == "METALS-TACTICAL-POLICY-V3-DECISION-UTILITY-ROW-LEVEL-AUTHORITY-RESOLUTION-AUDIT-1"
    assert payload["source_schema_audit_id"] == "METALS-TACTICAL-POLICY-V3-DECISION-UTILITY-SOURCE-RESOLUTION-AUDIT-1"
    assert payload["source_schema_audit_head"] == "13e68da8f7589a56dfe703a9a394fca7a679c89c"
    assert payload["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    assert payload["read_only"] is True


def test_questions_cover_remaining_decision_utility_authorities() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert set(payload["questions"]) == {
        "commodity_forecast_row_coverage",
        "vehicle_forecast_row_coverage",
        "commodity_forecast_bound_population",
        "vehicle_forecast_bound_population",
        "recommendation_rationale_population",
        "recommendation_risk_summary_population",
        "certified_external_numeric_current_price_schema",
        "certified_external_dated_price_history_schema",
    }


def test_semantic_rules_are_fail_closed() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert all(payload["semantic_rules"].values())
    assert payload["semantic_rules"]["price_semantics_is_not_numeric_price"] is True
    assert payload["semantic_rules"]["downside_penalty_is_not_forecast_lower_bound"] is True
    assert payload["semantic_rules"]["uncertainty_penalty_is_not_generic_risk_score"] is True
    assert payload["semantic_rules"]["no_data_is_synthesized"] is True


def test_all_write_and_deployment_boundaries_remain_closed() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert all(value is False for value in payload["controls"].values())


def test_audit_decision_and_next_decision() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert payload["decision"] == "AUTHORIZE_READ_ONLY_METALS_DECISION_UTILITY_ROW_LEVEL_AUTHORITY_RESOLUTION_AUDIT"
    assert payload["next_decision"] == "DESIGN_METALS_DECISION_UTILITY_COMPLETION_FROM_RESOLVED_AUTHORITIES"


def test_script_uses_duckdb_read_only() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "duckdb.connect(str(database), read_only=True)" in source
    assert "UPDATE " not in source
    assert "INSERT " not in source
    assert "DELETE FROM" not in source


def test_script_resolves_row_level_forecast_and_recommendation_coverage() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "FROM forecasts_current" in source
    assert "FROM recommendations_current" in source
    assert "WHERE universal_asset_id LIKE 'metals:%'" in source
    assert "non_null_lower_bound" in source
    assert "non_null_upper_bound" in source
    assert "rationale_nonblank_count" in source
    assert "risk_summary_nonblank_count" in source


def test_script_inspects_external_price_history_package_without_network() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "--price-package-root" in source
    assert "rglob(\"*.csv\")" in source
    assert "candidate_numeric_current_price" in source
    assert "candidate_dated_price_history" in source
    assert "requests" not in source
    assert "urllib" not in source


def test_script_will_not_overwrite_evidence() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "Output already exists and will not be overwritten" in source


def test_script_reports_expected_next_decision() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"next_decision": "DESIGN_METALS_DECISION_UTILITY_COMPLETION_FROM_RESOLVED_AUTHORITIES"' in source
