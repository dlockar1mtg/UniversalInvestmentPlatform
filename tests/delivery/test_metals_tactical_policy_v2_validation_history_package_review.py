import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "config" / "metals" / "tactical_policy_v2_validation_history_package_review.json"
REVIEWER = ROOT / "scripts" / "review_metals_tactical_policy_v2_validation_history_package.py"


def load_contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_package_hashes_and_boundary_are_locked():
    package = load_contract()["package_contract"]
    assert package["package_id"] == "metals-v2-validation-history-20191204-20230821"
    assert package["common_start_date"] == "2019-12-04"
    assert package["common_end_date"] == "2023-08-21"
    assert package["common_observation_count"] == 934
    assert package["expected_history_row_count"] == 10274
    assert package["history_sha256"] == "400aa5792533653eccf7bdfb3dd4b67fddb8f45ad138bda1a7d4ac1c1137bd62"
    assert package["coverage_sha256"] == "26477acb7f50169980ea6c1ede73b6cfac7ffbc21b34273a1253f1ffa6b5f9f9"
    assert package["manifest_sha256"] == "602521ce36c4f1cb0797dc29d932c803bd0e0a12c38652211c1cdd1cf32216dd"


def test_governed_symbol_set_and_roles_are_preserved():
    package = load_contract()["package_contract"]
    assert package["symbols"] == [
        "BIL", "COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM"
    ]
    assert package["vehicle_count"] == 11
    assert package["opportunity_vehicle_count"] == 10
    assert package["reference_control_asset_id"] == "metals:vehicle:BIL"


def test_review_is_structural_and_outcome_blind():
    review = load_contract()["review_requirements"]
    assert review["artifact_hashes_must_match"] is True
    assert review["exact_common_calendar_equality_required"] is True
    assert review["duplicate_ticker_date_rows_prohibited"] is True
    assert review["required_price_nulls_prohibited"] is True
    assert review["ohlc_consistency_required"] is True
    assert review["no_network_query_during_review"] is True
    assert review["no_candidate_posture_calculation_during_review"] is True
    assert review["no_forward_return_calculation_during_review"] is True
    assert review["no_mae_mfe_calculation_during_review"] is True


def test_review_does_not_authorize_evaluation_or_tactical_output():
    controls = load_contract()["controls"]
    assert controls["validation_package_review_authorized"] is True
    assert controls["historical_candidate_evaluation_authorized"] is False
    assert controls["new_validation_outcome_inspection_authorized"] is False
    assert controls["tactical_posture_authorized"] is False
    assert controls["production_database_write_authorized"] is False
    assert controls["cross_domain_rank_authorized"] is False
    assert controls["allocation_policy_authorized"] is False
    assert controls["automatic_execution_authorized"] is False


def test_reviewer_has_no_network_or_outcome_engine_imports():
    text = REVIEWER.read_text(encoding="utf-8")
    tree = ast.parse(text)
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    assert "yfinance" not in imported_roots
    assert "requests" not in imported_roots
    assert "httpx" not in imported_roots
    lowered = text.lower()
    assert "yf.download(" not in lowered
    assert ".history(" not in lowered
    assert ".pct_change(" not in lowered
    assert "forward_return_21" not in lowered
    assert "forward_return_63" not in lowered
    assert "candidate_posture =" not in lowered


def test_next_decision_restores_current_price_semantic_gate():
    contract = load_contract()
    assert contract["next_decision"] == "AUTHORIZE_METALS_CURRENT_PRICE_SEMANTIC_REVIEW"
