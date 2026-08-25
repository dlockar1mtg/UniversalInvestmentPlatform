from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_presentation_activation_authorization_design.json"
REVIEW_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_production_database_write_review.json"
READ_API_PATH = ROOT / "foundation" / "presentation" / "read_api.py"
REC_UI_PATH = ROOT / "foundation" / "production" / "dashboard_assets" / "recommendation_ui.js"

EXPECTED_DB_SHA = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
EXPECTED_STATE_SHA = "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a"
EXPECTED_MANIFEST_SHA = "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75"


def main() -> int:
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    read_api = READ_API_PATH.read_text(encoding="utf-8")
    rec_ui = REC_UI_PATH.read_text(encoding="utf-8")

    if design.get("design_id") != "METALS-TACTICAL-POLICY-V3-PRESENTATION-ACTIVATION-AUTHORIZATION-DESIGN-1":
        raise RuntimeError("unexpected presentation activation design id")
    if design.get("source_review_id") != review.get("review_id"):
        raise RuntimeError("presentation design source review mismatch")
    if design.get("source_review_decision") != review.get("review_decision"):
        raise RuntimeError("presentation design source review decision mismatch")
    if design.get("source_database_sha256") != EXPECTED_DB_SHA:
        raise RuntimeError("presentation design database SHA mismatch")
    if design.get("source_state_sha256") != EXPECTED_STATE_SHA:
        raise RuntimeError("presentation design state SHA mismatch")
    if design.get("source_manifest_sha256") != EXPECTED_MANIFEST_SHA:
        raise RuntimeError("presentation design manifest SHA mismatch")

    architecture = design.get("presentation_architecture", {})
    if architecture.get("record_type") != "tactical_state":
        raise RuntimeError("tactical state must remain a separate presentation record type")
    if architecture.get("domain_id") != "metals":
        raise RuntimeError("presentation activation must remain Metals-only")
    if architecture.get("source_relation") != "metals_tactical_state_current":
        raise RuntimeError("unexpected tactical source relation")
    for key in (
        "recommendation_catalog_payload_mutation_forbidden",
        "existing_recommendation_record_replacement_forbidden",
        "existing_forecast_record_replacement_forbidden",
        "existing_risk_record_replacement_forbidden",
        "cross_domain_rank_creation_forbidden",
    ):
        if architecture.get(key) is not True:
            raise RuntimeError(f"presentation architecture guardrail not true: {key}")

    if "def asset_detail" not in read_api or "GROUP" in ():
        raise RuntimeError("asset detail API contract missing")
    if "grouped.setdefault(str(record_type)" not in read_api:
        raise RuntimeError("asset detail does not support independent record types")
    if '@app.get("/v1/presentation/assets/{domain_id}/{asset_id}")' not in read_api:
        raise RuntimeError("asset detail endpoint missing")
    if "readAssetDetail" not in rec_ui or "/v1/presentation/assets/" not in rec_ui:
        raise RuntimeError("recommendation UI does not load asset detail")
    if "Long-term thesis + tactical opportunity" not in rec_ui:
        raise RuntimeError("Metals decision-utility framing missing")

    allowed = set(design.get("allowed_tactical_fields", []))
    for required in (
        "ticker", "as_of_date", "candidate_regime", "tactical_state", "state_available",
        "state_reason", "is_reference_control", "source_state_sha256",
        "source_materialization_manifest_sha256",
    ):
        if required not in allowed:
            raise RuntimeError(f"required tactical presentation field missing: {required}")

    for section in ("presentation_fail_closed_design", "semantic_guardrails"):
        for key, value in design.get(section, {}).items():
            if value is not True:
                raise RuntimeError(f"required presentation design control not true: {section}.{key}")

    boundary = design.get("authorization_boundary", {})
    if boundary.get("presentation_activation_design_complete") is not True:
        raise RuntimeError("presentation activation design is incomplete")
    for key in (
        "presentation_activation_authorization_created",
        "presentation_publication_implementation_authorized",
        "presentation_activation_authorized",
        "presentation_activation_executed",
        "analytical_database_write_authorized",
        "second_production_database_write_authorized",
        "network_collection_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        if boundary.get(key) is not False:
            raise RuntimeError(f"downstream authority prematurely enabled: {key}")

    if design.get("next_decision") != "CONSIDER_METALS_TACTICAL_POLICY_V3_PRESENTATION_ACTIVATION_AUTHORIZATION":
        raise RuntimeError("unexpected next decision")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "design_id": design["design_id"],
        "source_database_sha256": EXPECTED_DB_SHA,
        "source_state_sha256": EXPECTED_STATE_SHA,
        "source_manifest_sha256": EXPECTED_MANIFEST_SHA,
        "record_type": "tactical_state",
        "domain_id": "metals",
        "source_relation": "metals_tactical_state_current",
        "asset_detail_endpoint": "/v1/presentation/assets/{domain_id}/{asset_id}",
        "presentation_activation_design_complete": True,
        "presentation_activation_authorization_created": False,
        "presentation_activation_authorized": False,
        "analytical_database_write_authorized": False,
        "next_decision": "CONSIDER_METALS_TACTICAL_POLICY_V3_PRESENTATION_ACTIVATION_AUTHORIZATION",
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
