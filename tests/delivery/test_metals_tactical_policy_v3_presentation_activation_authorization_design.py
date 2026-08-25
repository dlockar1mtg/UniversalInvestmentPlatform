import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_presentation_activation_authorization_design.json"
READ_API_PATH = ROOT / "foundation" / "presentation" / "read_api.py"
REC_UI_PATH = ROOT / "foundation" / "production" / "dashboard_assets" / "recommendation_ui.js"


def load_design():
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


def test_design_binds_certified_postwrite_authority():
    design = load_design()
    assert design["design_id"] == "METALS-TACTICAL-POLICY-V3-PRESENTATION-ACTIVATION-AUTHORIZATION-DESIGN-1"
    assert design["source_review_id"] == "METALS-TACTICAL-POLICY-V3-PRODUCTION-DATABASE-WRITE-REVIEW-1"
    assert design["source_review_decision"] == "PRODUCTION_DATABASE_WRITE_CERTIFIED_FOR_PRESENTATION_ACTIVATION_CONSIDERATION"
    assert design["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    assert design["source_state_sha256"] == "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a"
    assert design["source_manifest_sha256"] == "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75"


def test_design_keeps_tactical_state_separate_from_existing_authorities():
    architecture = load_design()["presentation_architecture"]
    assert architecture["record_type"] == "tactical_state"
    assert architecture["domain_id"] == "metals"
    assert architecture["source_relation"] == "metals_tactical_state_current"
    assert architecture["recommendation_catalog_payload_mutation_forbidden"] is True
    assert architecture["existing_recommendation_record_replacement_forbidden"] is True
    assert architecture["existing_forecast_record_replacement_forbidden"] is True
    assert architecture["existing_risk_record_replacement_forbidden"] is True
    assert architecture["cross_domain_rank_creation_forbidden"] is True


def test_design_uses_existing_asset_detail_extension_point():
    read_api = READ_API_PATH.read_text(encoding="utf-8")
    ui = REC_UI_PATH.read_text(encoding="utf-8")
    assert "def asset_detail" in read_api
    assert "grouped.setdefault(str(record_type)" in read_api
    assert '@app.get("/v1/presentation/assets/{domain_id}/{asset_id}")' in read_api
    assert "readAssetDetail" in ui
    assert "/v1/presentation/assets/" in ui
    assert "Long-term thesis + tactical opportunity" in ui


def test_design_requires_explicit_no_overlay_and_reference_control_explanations():
    design = load_design()
    explanations = design["required_explanations"]
    assert "not a negative long-term thesis" in explanations["no_tactical_overlay"]
    assert "sell signal" in explanations["no_tactical_overlay"]
    assert "BIL is a reference/control vehicle" in explanations["bil_reference_control"]
    assert "does not replace the certified long-term recommendation" in explanations["tactical_layer_role"]


def test_design_fail_closed_and_semantic_guardrails_are_all_true():
    design = load_design()
    assert design["presentation_fail_closed_design"]
    assert design["semantic_guardrails"]
    assert all(value is True for value in design["presentation_fail_closed_design"].values())
    assert all(value is True for value in design["semantic_guardrails"].values())


def test_design_does_not_prematurely_authorize_activation_or_any_new_write():
    boundary = load_design()["authorization_boundary"]
    assert boundary["presentation_activation_design_complete"] is True
    forbidden = {key: value for key, value in boundary.items() if key != "presentation_activation_design_complete"}
    assert forbidden
    assert all(value is False for value in forbidden.values())


def test_design_next_decision_is_consider_activation_authorization():
    assert load_design()["next_decision"] == "CONSIDER_METALS_TACTICAL_POLICY_V3_PRESENTATION_ACTIVATION_AUTHORIZATION"
