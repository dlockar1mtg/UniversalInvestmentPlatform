from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_current_state_materialization_review.json"
VERIFIER_PATH = ROOT / "scripts" / "verify_metals_tactical_policy_v3_current_state_materialization_review.py"
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_post_validation_live_use_authorization.json"


def load_review() -> dict:
    return json.loads(REVIEW_PATH.read_text(encoding="utf-8"))


def test_review_and_verifier_parse() -> None:
    json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    ast.parse(VERIFIER_PATH.read_text(encoding="utf-8"))


def test_review_binds_exact_materialization_artifacts() -> None:
    review = load_review()
    assert review["review_id"] == "METALS-TACTICAL-POLICY-V3-CURRENT-STATE-MATERIALIZATION-REVIEW-1"
    assert review["source_materialization_id"] == "METALS-TACTICAL-POLICY-V3-CURRENT-STATE-MATERIALIZATION-1"
    assert review["source_materialization_state_sha256"] == "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a"
    assert review["source_materialization_manifest_sha256"] == "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75"
    assert review["source_materialization_as_of_date"] == "2026-08-21"
    assert review["source_package_id"] == "metals-price-history-20260824"


def test_review_preserves_locked_policy_versions() -> None:
    review = load_review()
    assert review["source_classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1"
    assert review["source_action_mapping_version"] == "METALS-V3-ACTION-MAPPING-1"


def test_review_observes_exact_neutral_current_state() -> None:
    observed = load_review()["observed_materialization"]
    assert observed["row_count"] == 11
    assert observed["opportunity_row_count"] == 10
    assert observed["reference_control_row_count"] == 1
    assert observed["directional_opportunity_row_count"] == 0
    assert observed["state_counts"] == {"NO_TACTICAL_OVERLAY": 11}
    assert observed["all_opportunity_rows_non_directional"] is True
    assert observed["bil_reference_control_only"] is True
    assert observed["point_in_time_state"] is True
    assert observed["price_basis"] == "UNADJUSTED_CLOSE"


def test_review_accepts_neutral_state_without_overclaiming() -> None:
    review = load_review()
    findings = review["review_findings"]
    guards = review["interpretation_guardrails"]
    assert findings["current_all_neutral_result_is_semantically_valid"] is True
    assert findings["no_directional_state_is_not_a_failure_condition"] is True
    assert guards["no_tactical_overlay_does_not_mean_negative_long_term_thesis"] is True
    assert guards["no_tactical_overlay_does_not_mean_negative_medium_term_opportunity"] is True
    assert guards["no_tactical_overlay_does_not_mean_sell"] is True
    assert guards["no_tactical_overlay_does_not_mean_zero_expected_return"] is True


def test_review_allows_only_persistence_consideration() -> None:
    review = load_review()
    assert review["review_decision"] == "CURRENT_STATE_MATERIALIZATION_APPROVED_FOR_PRODUCTION_PERSISTENCE_CONSIDERATION"
    controls = review["controls"]
    assert controls["current_state_materialization_review_passed"] is True
    assert controls["production_persistence_consideration_authorized"] is True
    for key, value in controls.items():
        if key in {"current_state_materialization_review_passed", "production_persistence_consideration_authorized"}:
            continue
        assert value is False


def test_review_scope_excludes_write_presentation_network_and_retraining() -> None:
    scope = load_review()["review_scope"]
    assert scope["semantic_review"] is True
    assert scope["operational_review"] is True
    assert scope["production_persistence_consideration_only"] is True
    assert scope["presentation_activation_review"] is False
    assert scope["database_write_execution"] is False
    assert scope["network_collection"] is False
    assert scope["model_retraining"] is False


def test_live_use_authorization_remains_source_authority() -> None:
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    review = load_review()
    assert auth["authorization_id"] == review["source_live_use_authorization_id"]
    assert auth["authorized_live_use"]["current_state_materialization_authorized"] is True
    assert auth["authorized_live_use"]["live_tactical_posture_authorized"] is True
    assert auth["downstream_authorization_boundary"]["production_database_write_authorized"] is False
    assert auth["downstream_authorization_boundary"]["presentation_activation_authorized"] is False


def test_next_decision_is_persistence_authorization_design() -> None:
    assert load_review()["next_decision"] == "DESIGN_METALS_TACTICAL_POLICY_V3_PRODUCTION_PERSISTENCE_AUTHORIZATION"
