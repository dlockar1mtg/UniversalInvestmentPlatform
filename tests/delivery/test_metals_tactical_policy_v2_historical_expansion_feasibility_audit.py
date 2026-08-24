from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "metals" / "tactical_policy_v2_historical_expansion_feasibility_audit.json"
SCRIPT = ROOT / "scripts" / "audit_metals_tactical_policy_v2_historical_expansion_feasibility.py"


def test_files_exist():
    assert CONFIG.is_file()
    assert SCRIPT.is_file()


def test_contract_locks_pre_v1_boundary_and_outcome_blindness():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert cfg["audit_id"] == "METALS-TACTICAL-POLICY-V2-HISTORICAL-EXPANSION-FEASIBILITY-AUDIT-1"
    assert cfg["source_candidate_rule_design"] == "METALS-TACTICAL-POLICY-V2-CANDIDATE-RULE-DESIGN-1"
    assert cfg["maximum_feasibility_end_date"] == "2023-08-21"
    assert len(cfg["vehicle_symbols"]) == 11
    assert cfg["reference_control_symbols"] == ["BIL"]
    rules = cfg["feasibility_rules"]
    assert rules["network_history_availability_probe_authorized"] is True
    assert rules["price_or_return_outcomes_may_not_be_reported"] is True
    assert rules["candidate_postures_may_not_be_calculated"] is True
    assert rules["forward_returns_may_not_be_calculated"] is True
    assert rules["historical_expansion_may_not_be_persisted"] is True
    assert rules["v1_interval_overlap_prohibited"] is True


def test_controls_do_not_authorize_collection_or_policy():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    controls = cfg["controls"]
    assert controls["historical_expansion_feasibility_audit_authorized"] is True
    assert controls["network_history_availability_probe_authorized"] is True
    for key in (
        "historical_expansion_execution_authorized",
        "new_validation_outcome_inspection_authorized",
        "historical_candidate_evaluation_authorized",
        "tactical_posture_authorized",
        "presentation_activation_authorized",
        "production_database_write_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        assert controls[key] is False


def test_script_reports_only_availability_metadata():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "yf.download" in text
    assert '"price_values_reported": False' in text
    assert '"return_outcomes_reported": False' in text
    assert '"candidate_postures_calculated": False' in text
    assert '"forward_returns_calculated": False' in text
    assert '"historical_expansion_persisted": False' in text
    assert "to_csv" not in text
    assert "to_parquet" not in text
    assert "duckdb" not in text.lower()
