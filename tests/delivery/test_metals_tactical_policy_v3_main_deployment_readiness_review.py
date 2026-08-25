from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "config" / "metals" / "tactical_policy_v3_main_deployment_readiness_review.json"
READ_API = ROOT / "foundation" / "presentation" / "read_api.py"
TACTICAL_UI = ROOT / "foundation" / "production" / "dashboard_assets" / "metals_tactical_ui.js"
RECOMMENDATION_UI = ROOT / "foundation" / "production" / "dashboard_assets" / "recommendation_ui.js"


def load_review():
    return json.loads(REVIEW.read_text(encoding="utf-8"))


def test_review_fails_closed_for_main_deployment():
    review = load_review()
    assert review["review_id"] == "METALS-TACTICAL-POLICY-V3-MAIN-DEPLOYMENT-READINESS-REVIEW-1"
    assert review["readiness_decision"] == "NOT_READY_REQUIRES_EXPLICIT_RECOMMENDATION_UI_TACTICAL_INTEGRATION"
    assert review["main_deployment_authorized"] is False
    assert review["whole_research_branch_merge_authorized"] is False
    assert review["next_decision"] == "IMPLEMENT_METALS_V3_RECOMMENDATION_UI_TACTICAL_INTEGRATION"


def test_backend_asset_detail_already_supports_tactical_state_records():
    source = READ_API.read_text(encoding="utf-8")
    assert "SELECT record_type, record_key, payload_json" in source
    assert 'grouped.setdefault(str(record_type), [])' in source


def test_tactical_helper_has_semantic_render_entry_point():
    source = TACTICAL_UI.read_text(encoding="utf-8")
    assert 'const RECORD_TYPE="tactical_state"' in source
    assert "renderTacticalPanel" in source
    assert "window.UIPMetalsTactical" in source
    assert "not a negative long-term thesis" in source


def test_recommendation_ui_integration_is_currently_missing():
    source = RECOMMENDATION_UI.read_text(encoding="utf-8")
    assert "UIPMetalsTactical.renderTacticalPanel" not in source


def test_candidate_deployment_package_is_bounded_to_four_runtime_files():
    review = load_review()
    assert review["bounded_candidate_deployment_files"] == [
        "foundation/production/http_service.py",
        "foundation/production/dashboard_assets/dashboard.html",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
        "foundation/production/dashboard_assets/recommendation_ui.js",
    ]


def test_data_and_model_mutations_remain_out_of_scope():
    controls = load_review()["controls"]
    assert all(value is False for value in controls.values())
