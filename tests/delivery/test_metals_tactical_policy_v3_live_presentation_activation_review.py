import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_live_presentation_activation_review.json"
RENDER_PATH = ROOT / "render.yaml"
MAIN_HTTP_EXPECTED_ABSENT = '/dashboard/assets/metals_tactical_ui.js'


def load_review():
    return json.loads(REVIEW_PATH.read_text(encoding="utf-8"))


def test_successful_hosted_activation_is_frozen():
    review = load_review()
    active = review["active_publication"]
    assert review["source_authorization_consumed"] is True
    assert active["publication_id"] == "metals-v3-live-tactical-r2-20260825"
    assert active["publication_status"] == "ACTIVE"
    assert active["content_fingerprint"] == "21a3e3c8a1e73b7370d23f0704081f7ac01f28609bed22f94d00d4f4c2e7c126"
    assert active["record_count"] == 4181
    assert active["metals_tactical_state_count"] == 10
    assert active["metals_recommendation_count"] == 12
    assert active["metals_forecast_count"] == 16
    assert active["metals_risk_count"] == 11
    assert active["active_pointer_count"] == 1
    assert active["active_status_count"] == 1


def test_previous_publication_is_preserved_as_superseded():
    previous = load_review()["previous_publication"]
    assert previous["publication_id"] == "dash-read-1-metals-price-history-dff98e56d27c"
    assert previous["publication_status"] == "SUPERSEDED"


def test_tactical_semantics_remain_bounded():
    semantic = load_review()["semantic_state"]
    assert semantic["bil_projected_as_opportunity"] is False
    assert semantic["all_tactical_states"] == "NO_TACTICAL_OVERLAY"
    assert semantic["all_tactical_regimes"] == "NEUTRAL_OR_UNCERTAIN"
    assert semantic["tactical_tickers"] == ["COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM"]


def test_render_deploys_main_and_visual_live_state_is_not_overclaimed():
    review = load_review()
    deployment = review["deployment_state"]
    render = RENDER_PATH.read_text(encoding="utf-8")
    assert "branch: main" in render
    assert deployment["render_configured_branch"] == "main"
    assert deployment["hosted_presentation_data_active"] is True
    assert deployment["metals_tactical_ui_route_present_on_main"] is False
    assert deployment["metals_tactical_ui_script_present_on_main"] is False
    assert deployment["visual_dashboard_live_certified"] is False


def test_activation_cannot_be_reexecuted_and_next_step_is_main_deployment():
    review = load_review()
    assert review["controls"]["activation_may_be_reexecuted"] is False
    assert review["controls"]["main_deployment_may_be_considered"] is True
    assert review["review_decision"] == "HOSTED_PRESENTATION_ACTIVATION_CERTIFIED_UI_DEPLOYMENT_TO_MAIN_REQUIRED"
    assert review["next_decision"] == "CERTIFY_METALS_V3_MAIN_DEPLOYMENT_READINESS"
