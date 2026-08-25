from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_production_database_write_review.json"
VERIFIER_PATH = ROOT / "scripts" / "verify_metals_tactical_policy_v3_production_database_write_review.py"


def load_review() -> dict:
    return json.loads(REVIEW_PATH.read_text(encoding="utf-8"))


def test_review_binds_exact_postwrite_authority() -> None:
    review = load_review()
    assert review["review_id"] == "METALS-TACTICAL-POLICY-V3-PRODUCTION-DATABASE-WRITE-REVIEW-1"
    assert review["source_authorization_head"] == "4d9cbfe35d8f564c2a524fa0ddd7b00a2cb6a2e9"
    assert review["source_state_sha256"] == "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a"
    assert review["source_manifest_sha256"] == "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75"
    assert review["prewrite_database_sha256"] == "dff98e56d27cbc5ef879c18939309c5ab8661fa8fa6dfe74e82537fd53954f7c"
    assert review["postwrite_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def test_review_certifies_exact_persisted_shape() -> None:
    observed = load_review()["observed_production_state"]
    assert observed["history_table"] == "metals_tactical_state_history"
    assert observed["current_view"] == "metals_tactical_state_current"
    assert observed["history_row_count"] == 11
    assert observed["current_row_count"] == 11
    assert observed["opportunity_row_count"] == 10
    assert observed["reference_control_row_count"] == 1
    assert observed["neutral_row_count"] == 11
    assert observed["directional_opportunity_row_count"] == 0
    assert observed["distinct_state_hash_count"] == 1
    assert observed["distinct_manifest_hash_count"] == 1
    assert observed["exact_import_id_count"] == 1
    assert observed["authorization_consumed"] is True
    assert observed["second_execution_forbidden"] is True
    assert observed["history_append_only"] is True
    assert observed["source_lineage_verified"] is True


def test_review_preserves_semantic_separation() -> None:
    findings = load_review()["semantic_findings"]
    assert findings and all(value is True for value in findings.values())


def test_review_only_authorizes_presentation_consideration() -> None:
    review = load_review()
    assert review["review_decision"] == "PRODUCTION_DATABASE_WRITE_CERTIFIED_FOR_PRESENTATION_ACTIVATION_CONSIDERATION"
    controls = review["controls"]
    assert controls["production_database_write_certified"] is True
    assert controls["production_database_write_authorization_consumed"] is True
    assert controls["presentation_activation_consideration_authorized"] is True
    assert controls["second_production_database_write_authorized"] is False
    assert controls["presentation_activation_authorized"] is False
    assert controls["presentation_activation_executed"] is False
    assert controls["network_collection_authorized"] is False
    assert controls["forecast_refresh_authorized"] is False
    assert controls["model_retraining_authorized"] is False
    assert controls["cross_domain_rank_authorized"] is False
    assert controls["allocation_policy_authorized"] is False
    assert controls["automatic_execution_authorized"] is False
    assert review["next_decision"] == "DESIGN_METALS_TACTICAL_POLICY_V3_PRESENTATION_ACTIVATION_AUTHORIZATION"


def test_review_verifier_is_read_only() -> None:
    text = VERIFIER_PATH.read_text(encoding="utf-8").lower()
    for forbidden in (
        "duckdb.connect",
        "insert into metals_tactical_state_history",
        "delete from metals_tactical_state_history",
        "update metals_tactical_state_history",
        "create table",
        "create or replace view",
    ):
        assert forbidden not in text
    assert '"read_only": true' in text
