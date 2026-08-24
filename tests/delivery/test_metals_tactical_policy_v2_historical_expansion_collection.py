import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "config" / "metals" / "tactical_policy_v2_historical_expansion_collection.json"
SCRIPT = ROOT / "scripts" / "collect_metals_tactical_policy_v2_historical_expansion.py"


def load_auth():
    return json.loads(AUTH.read_text(encoding="utf-8"))


def test_collection_authority_is_exact_and_disjoint():
    auth = load_auth()
    assert auth["collection_id"] == "METALS-TACTICAL-POLICY-V2-HISTORICAL-EXPANSION-COLLECTION-1"
    assert auth["source_collection_design"] == "METALS-TACTICAL-POLICY-V2-HISTORICAL-EXPANSION-COLLECTION-DESIGN-1"
    boundary = auth["collection_boundary"]
    assert boundary["common_start_date"] == "2019-12-04"
    assert boundary["common_end_date"] == "2023-08-21"
    assert boundary["existing_certified_history_start_date"] == "2023-08-22"
    assert boundary["expected_common_observation_count"] == 934
    assert boundary["interval_disjoint_from_v1"] is True


def test_collection_symbols_and_package_are_locked():
    auth = load_auth()
    assert auth["package_id"] == "metals-v2-validation-history-20191204-20230821"
    assert auth["source_contract"]["symbols"] == [
        "BIL", "COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM"
    ]
    assert auth["source_contract"]["provider"] == "yfinance"
    assert auth["artifact_contract"]["common_calendar_intersection_required"] is True
    assert auth["artifact_contract"]["missing_rows_may_not_be_synthesized"] is True
    assert auth["artifact_contract"]["exact_common_observation_count_required"] is True


def test_collection_authorizes_only_raw_history_collection():
    controls = load_auth()["controls"]
    assert controls["historical_expansion_collection_authorized"] is True
    assert controls["validation_package_review_authorized"] is False
    assert controls["historical_candidate_evaluation_authorized"] is False
    assert controls["tactical_posture_authorized"] is False
    assert controls["presentation_activation_authorized"] is False
    assert controls["production_database_write_authorized"] is False
    assert controls["forecast_refresh_authorized"] is False
    assert controls["model_retraining_authorized"] is False
    assert controls["cross_domain_rank_authorized"] is False
    assert controls["allocation_policy_authorized"] is False
    assert controls["automatic_execution_authorized"] is False


def test_collection_script_uses_network_source_but_no_policy_logic():
    text = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(text)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert "yfinance" in imported
    lowered = text.lower()
    assert "yf.download(" in lowered
    assert "candidate_postures_calculated\": false" in lowered
    assert "forward_returns_calculated\": false" in lowered
    assert "policy_pass_fail_checks_calculated\": false" in lowered
    assert ".pct_change(" not in lowered
    assert ".rolling(" not in lowered
    assert "maximum_adverse_excursion_pct" not in lowered
    assert "maximum_favorable_excursion_pct" not in lowered


def test_collection_script_is_package_only_not_database_or_presentation():
    lowered = SCRIPT.read_text(encoding="utf-8").lower()
    assert "duckdb" not in lowered
    assert "psycopg" not in lowered
    assert "presentationreadrepository" not in lowered
    assert "uiip_database_url" not in lowered
    assert "insert into" not in lowered
    assert "update " not in lowered
    assert "delete from" not in lowered
