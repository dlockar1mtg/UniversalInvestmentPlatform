from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_integration_record_binds_certified_readiness_review_and_live_publication():
    record = json.loads(read("config/metals/tactical_policy_v3_recommendation_ui_tactical_integration.json"))
    assert record["implementation_id"] == "METALS-TACTICAL-POLICY-V3-RECOMMENDATION-UI-TACTICAL-INTEGRATION-1"
    assert record["source_readiness_review_id"] == "METALS-TACTICAL-POLICY-V3-MAIN-DEPLOYMENT-READINESS-REVIEW-1"
    assert record["source_readiness_review_head"] == "c13ccd0dcdc0fd02854ece852910c85780162815"
    assert record["active_publication_id"] == "metals-v3-live-tactical-r2-20260825"


def test_metals_catalog_exposes_research_action_and_binds_click_to_metals_detail():
    source = read("foundation/production/dashboard_assets/recommendation_ui.js")
    assert 'rec-metals-detail' in source
    assert 'openMetalsDetail(button.dataset.assetId)' in source
    assert 'async function openMetalsDetail(assetId)' in source


def test_metals_detail_uses_existing_asset_detail_and_explicit_tactical_renderer():
    source = read("foundation/production/dashboard_assets/recommendation_ui.js")
    assert 'await readAssetDetail(item)' in source
    assert 'window.UIPMetalsTactical?.renderTacticalPanel' in source
    assert 'renderTactical(detail)' in source
    assert 'const tacticalPanel=renderTactical(detail)' in source
    assert '${tacticalPanel}' in source


def test_metals_detail_preserves_long_term_authority_and_tactical_separation():
    source = read("foundation/production/dashboard_assets/recommendation_ui.js")
    assert 'Long-term thesis' in source
    assert 'native recommendation, forecast, and risk evidence remain the strategic authority' in source
    assert 'Tactical state is shown separately and does not overwrite them.' in source
    assert 'Tactical supportive, defensive, or no-overlay states are relative tactical interpretations only.' in source
    assert 'They are not buy/sell instructions, position sizing, automatic execution authority' in source


def test_missing_tactical_renderer_fails_closed_without_reinterpreting_long_term_data():
    source = read("foundation/production/dashboard_assets/recommendation_ui.js")
    assert 'typeof renderTactical!=="function"' in source
    assert 'Certified Metals tactical renderer is unavailable. Long-term recommendation data was not altered.' in source


def test_helper_semantics_still_enforce_no_overlay_boundaries():
    helper = read("foundation/production/dashboard_assets/metals_tactical_ui.js")
    assert 'const RECORD_TYPE="tactical_state"' in helper
    assert 'function renderTacticalPanel(detail)' in helper
    assert 'No tactical overlay means' in helper
    assert 'not a negative long-term thesis' in helper
    assert 'sell signal' in helper
    assert 'zero expected return' in helper
    assert 'allocation instruction' in helper


def test_deployment_remains_unexecuted_and_bounded_to_four_runtime_files():
    record = json.loads(read("config/metals/tactical_policy_v3_recommendation_ui_tactical_integration.json"))
    assert record["deployment_boundary"]["main_deployment_authorized"] is False
    assert record["deployment_boundary"]["whole_research_branch_merge_authorized"] is False
    assert record["deployment_boundary"]["hosted_presentation_reactivation_authorized"] is False
    assert len(record["candidate_runtime_files_after_integration"]) == 4
    assert record["next_decision"] == "CERTIFY_METALS_V3_RECOMMENDATION_UI_TACTICAL_INTEGRATION"
