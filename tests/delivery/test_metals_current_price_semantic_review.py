import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "config" / "metals" / "current_price_semantic_review.json"
REVIEWER = ROOT / "scripts" / "review_metals_current_price_semantics.py"


def load_contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_semantic_target_is_unadjusted_close():
    semantic = load_contract()["semantic_target"]
    assert semantic["published_field"] == "current_price_usd"
    assert semantic["required_basis"] == "UNADJUSTED_CLOSE"
    assert semantic["history_reference_field"] == "close_usd"
    assert semantic["comparison_field"] == "adjusted_close_usd"
    assert semantic["classifications"] == ["RAW_CLOSE", "ADJUSTED_CLOSE", "BOTH", "NEITHER"]


def test_source_package_hashes_are_locked():
    source = load_contract()["source_package"]
    assert source["package_id"] == "metals-price-history-20260824"
    assert source["current_sha256"] == "e18ece1a8dbc5b23f6ec7bb2d014822bdccd8a7f82fca0b6c23d5fda3bc8a4ed"
    assert source["history_sha256"] == "c3749acbcf3a6d11ee9a6ca392b8421e7654936af489fbb93a2f4ae659470f31"
    assert source["manifest_sha256"] == "82ead8e711e0fde4b30fa4e0e7196681e41e7f0ffa363af201c0ee0737473dcf"
    assert source["expected_vehicle_count"] == 11


def test_certification_is_fail_closed_on_non_raw_close():
    rules = load_contract()["certification_rule"]
    assert rules["adjusted_only_match_is_failure"] is True
    assert rules["neither_match_is_failure"] is True
    assert rules["synthetic_correction_prohibited"] is True
    assert rules["presentation_correction_required_if_not_certified"] is True


def test_review_does_not_authorize_downstream_operations():
    controls = load_contract()["controls"]
    assert controls["semantic_review_authorized"] is True
    assert controls["native_source_query_authorized"] is False
    assert controls["package_regeneration_authorized"] is False
    assert controls["presentation_activation_authorized"] is False
    assert controls["production_database_write_authorized"] is False
    assert controls["historical_candidate_evaluation_authorized"] is False
    assert controls["new_validation_outcome_inspection_authorized"] is False
    assert controls["tactical_posture_authorized"] is False
    assert controls["cross_domain_rank_authorized"] is False
    assert controls["allocation_policy_authorized"] is False
    assert controls["automatic_execution_authorized"] is False


def test_reviewer_has_no_network_or_database_imports():
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
    assert "psycopg" not in imported_roots
    assert "duckdb" not in imported_roots


def test_next_decisions_are_explicit_for_both_semantic_results():
    contract = load_contract()
    assert contract["next_decision_if_certified"] == "AUTHORIZE_METALS_TACTICAL_POLICY_V2_VALIDATION_EVALUATION_DESIGN"
    assert contract["next_decision_if_not_certified"] == "REQUIRE_METALS_CURRENT_PRICE_RAW_CLOSE_EXPORT_CORRECTION"
