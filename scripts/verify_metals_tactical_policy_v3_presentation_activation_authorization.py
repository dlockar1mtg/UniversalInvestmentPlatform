from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_presentation_activation_authorization.json"

EXPECTED_DB_SHA = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
EXPECTED_STATE_SHA = "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a"
EXPECTED_MANIFEST_SHA = "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75"


def main() -> int:
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))

    if auth.get("authorization_id") != "METALS-TACTICAL-POLICY-V3-PRESENTATION-ACTIVATION-AUTHORIZATION-1":
        raise RuntimeError("unexpected presentation authorization ID")
    if auth.get("source_design_id") != "METALS-TACTICAL-POLICY-V3-PRESENTATION-ACTIVATION-AUTHORIZATION-DESIGN-1":
        raise RuntimeError("unexpected source design ID")
    if auth.get("source_design_head") != "ddba473097b1e7ae3656bd0f327942a98b847c0a":
        raise RuntimeError("unexpected source design HEAD")
    if auth.get("source_database_sha256") != EXPECTED_DB_SHA:
        raise RuntimeError("source database SHA changed")
    if auth.get("source_state_sha256") != EXPECTED_STATE_SHA:
        raise RuntimeError("source state SHA changed")
    if auth.get("source_manifest_sha256") != EXPECTED_MANIFEST_SHA:
        raise RuntimeError("source manifest SHA changed")
    if auth.get("authorization_decision") != "AUTHORIZE_METALS_V3_PRESENTATION_IMPLEMENTATION_ONLY":
        raise RuntimeError("unexpected presentation authorization decision")

    impl = auth.get("authorized_presentation_implementation", {})
    expected_impl = {
        "record_type": "tactical_state",
        "domain_id": "metals",
        "source_relation": "metals_tactical_state_current",
        "asset_detail_endpoint": "/v1/presentation/assets/{domain_id}/{asset_id}",
    }
    for key, value in expected_impl.items():
        if impl.get(key) != value:
            raise RuntimeError(f"unexpected presentation implementation field: {key}")
    for key in (
        "presentation_publication_implementation_authorized",
        "non_active_publication_validation_authorized",
        "recommendation_ui_metals_tactical_rendering_authorized",
        "aggregate_neutral_count_rendering_authorized",
    ):
        if impl.get(key) is not True:
            raise RuntimeError(f"presentation implementation authority missing: {key}")

    for key, value in auth.get("required_implementation_controls", {}).items():
        if value is not True:
            raise RuntimeError(f"required implementation control not true: {key}")
    for key, value in auth.get("semantic_guardrails", {}).items():
        if value is not True:
            raise RuntimeError(f"semantic guardrail not true: {key}")

    boundary = auth.get("authorization_boundary", {})
    if boundary.get("presentation_activation_authorization_created") is not True:
        raise RuntimeError("presentation authorization not created")
    if boundary.get("presentation_publication_implementation_authorized") is not True:
        raise RuntimeError("presentation implementation not authorized")
    for key in (
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

    if auth.get("next_decision") != "IMPLEMENT_METALS_TACTICAL_POLICY_V3_PRESENTATION_PUBLICATION_AND_UI":
        raise RuntimeError("unexpected next decision")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "authorization_id": auth["authorization_id"],
        "authorization_decision": auth["authorization_decision"],
        "source_database_sha256": auth["source_database_sha256"],
        "source_state_sha256": auth["source_state_sha256"],
        "source_manifest_sha256": auth["source_manifest_sha256"],
        "record_type": impl["record_type"],
        "domain_id": impl["domain_id"],
        "source_relation": impl["source_relation"],
        "presentation_publication_implementation_authorized": True,
        "non_active_publication_validation_authorized": True,
        "presentation_activation_authorized": False,
        "analytical_database_write_authorized": False,
        "next_decision": auth["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
