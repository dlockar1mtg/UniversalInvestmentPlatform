from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "config" / "metals" / "composite_presentation_staging_authorization.json"


def load_doc() -> dict:
    return json.loads(AUTH.read_text(encoding="utf-8"))


def test_candidate_binding_and_certification() -> None:
    doc = load_doc()
    candidate = doc["candidate"]
    cert = doc["candidate_certification"]
    assert doc["authorization_id"] == "METALS-COMPOSITE-PRESENTATION-STAGING-AUTHORIZATION-1"
    assert doc["source_governed_head"] == "f133181af9cf53e96c5fa2bf769eaa27824bd3d5"
    assert candidate["publication_id"] == "metals-mtg-composite-recovery-r1-20260828"
    assert candidate["record_count"] == 13264
    assert candidate["content_fingerprint"] == "67352221b51e7479fe9e154e12dd718a9cf392c794d2320461203fe980bfc009"
    assert cert == {
        "active_records_preserved": 13252,
        "metals_recommendations_replaced": 12,
        "metals_final_action_match_count": 12,
        "mtg_premium_record_count": 787,
        "other_active_records_changed": 0,
        "certified_records_missing": 0,
        "local_candidate_certification_passed": True,
    }


def test_staging_contract_requires_validation_and_preserves_pointer() -> None:
    doc = load_doc()
    contract = doc["staging_contract"]
    assert contract["stage_as_new_publication_only"] is True
    assert contract["required_publication_id"] == "metals-mtg-composite-recovery-r1-20260828"
    assert contract["required_record_count"] == 13264
    assert contract["required_content_fingerprint"] == "67352221b51e7479fe9e154e12dd718a9cf392c794d2320461203fe980bfc009"
    assert contract["validate_staged_record_count"] is True
    assert contract["validate_three_domain_health_records"] is True
    assert contract["validate_nonempty_asset_surface_for_crypto_metals_mtg"] is True
    assert contract["validate_metals_final_actions_12_of_12"] is True
    assert contract["validate_mtg_premium_records_787_of_787"] is True
    assert contract["active_pointer_must_remain_source_active_after_staging"] is True


def test_authorization_opens_staging_only() -> None:
    doc = load_doc()
    scope = doc["authorization_scope"]
    assert scope["read_hosted_presentation_records_authorized"] is True
    assert scope["hosted_publication_stage_authorized"] is True
    assert scope["hosted_staged_publication_validation_authorized"] is True
    for key in (
        "hosted_publication_activation_authorized",
        "active_pointer_mutation_authorized",
        "repository_code_change_authorized",
        "analytical_database_write_authorized",
        "model_refresh_authorized",
        "forecast_refresh_authorized",
        "recommendation_recompute_authorized",
        "mtg_premium_recompute_authorized",
        "manual_render_deployment_authorized",
        "allocation_or_execution_authorized",
    ):
        assert scope[key] is False
    assert doc["authorization_decision"] == "AUTHORIZE_BOUNDED_COMPOSITE_PRESENTATION_STAGING"
    assert doc["next_decision"] == "STAGE_AND_CERTIFY_BOUNDED_COMPOSITE_PRESENTATION_RECOVERY_CANDIDATE"
