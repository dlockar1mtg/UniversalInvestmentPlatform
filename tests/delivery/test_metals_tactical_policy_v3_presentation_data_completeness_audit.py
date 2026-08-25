from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_audit_contract_is_read_only_and_bound_to_certified_authority():
    payload = json.loads(read("config/metals/tactical_policy_v3_presentation_data_completeness_audit.json"))
    assert payload["audit_id"] == "METALS-TACTICAL-POLICY-V3-PRESENTATION-DATA-COMPLETENESS-AUDIT-1"
    assert payload["source_visual_preview_head"] == "e8a80f88e39b6d9dbfcc83400bc0c93d7335ec35"
    assert payload["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    assert payload["read_only"] is True
    assert all(value is False for value in payload["controls"].values())


def test_audit_targets_dashboard_blank_fields():
    payload = json.loads(read("config/metals/tactical_policy_v3_presentation_data_completeness_audit.json"))
    required = {
        "current_price", "return_1m_pct", "return_3m_pct", "return_6m_pct",
        "current_drawdown_pct", "distance_ma50_pct", "distance_ma200_pct",
        "realized_volatility_3m_pct", "candidate_regime", "tactical_state",
        "forecast_point", "forecast_expected_return", "forecast_lower_bound",
        "forecast_upper_bound", "rationale", "risk",
    }
    assert required.issubset(set(payload["target_fields"]))


def test_audit_script_opens_duckdb_read_only_and_discovers_sources():
    source = read("scripts/audit_metals_presentation_data_completeness.py")
    assert "duckdb.connect(str(path), read_only=True)" in source
    assert "candidate_sources_by_dashboard_field" in source
    assert "metals_tactical_state_current" in source
    assert "information_schema.tables" in source
    assert "DESIGN_METALS_PRESENTATION_DATA_COMPLETENESS_REMEDIATION" in source
    lowered = source.lower()
    assert "insert into" not in lowered
    assert "update " not in lowered
    assert "delete from" not in lowered
    assert "create table" not in lowered


def test_known_certified_surfaces_are_audited():
    source = read("scripts/audit_metals_presentation_data_completeness.py")
    for table in (
        "metals_forecast_model_component_current",
        "metals_regime_probability_current",
        "metals_uncertainty_adjusted_view_current",
        "metals_recommendation_change_current",
        "metals_data_freshness_current",
        "metals_platform_health_current",
        "metals_tactical_state_current",
    ):
        assert table in source
