from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> None:
    record = json.loads(read("config/metals/tactical_policy_v3_recommendation_ui_tactical_integration.json"))
    source = read("foundation/production/dashboard_assets/recommendation_ui.js")
    helper = read("foundation/production/dashboard_assets/metals_tactical_ui.js")

    assert record["implementation_id"] == "METALS-TACTICAL-POLICY-V3-RECOMMENDATION-UI-TACTICAL-INTEGRATION-1"
    assert record["source_readiness_review_head"] == "c13ccd0dcdc0fd02854ece852910c85780162815"
    assert record["active_publication_id"] == "metals-v3-live-tactical-r2-20260825"
    assert record["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"

    assert 'class="secondary rec-metals-detail"' in source
    assert 'async function openMetalsDetail(assetId)' in source
    assert 'await readAssetDetail(item)' in source
    assert 'window.UIPMetalsTactical?.renderTacticalPanel' in source
    assert 'renderTactical(detail)' in source
    assert 'tacticalPanel' in source
    assert 'Long-term thesis' in source
    assert 'Tactical state is shown separately and does not overwrite them.' in source
    assert 'Certified Metals tactical renderer is unavailable. Long-term recommendation data was not altered.' in source
    assert 'Tactical supportive, defensive, or no-overlay states are relative tactical interpretations only.' in source
    assert 'buy/sell instructions' in source
    assert 'position sizing' in source
    assert 'automatic execution authority' in source

    assert 'const RECORD_TYPE="tactical_state"' in helper
    assert 'function renderTacticalPanel(detail)' in helper
    assert 'No tactical overlay means' in helper
    assert 'not a negative long-term thesis' in helper

    boundary = record["deployment_boundary"]
    assert boundary["main_deployment_authorized"] is False
    assert boundary["whole_research_branch_merge_authorized"] is False
    assert boundary["hosted_presentation_reactivation_authorized"] is False
    assert boundary["analytical_database_write_authorized"] is False
    assert boundary["second_metals_production_write_authorized"] is False

    assert len(record["candidate_runtime_files_after_integration"]) == 4
    assert record["next_decision"] == "CERTIFY_METALS_V3_RECOMMENDATION_UI_TACTICAL_INTEGRATION"

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "implementation_id": record["implementation_id"],
        "metals_research_action_present": True,
        "existing_asset_detail_endpoint_used": True,
        "tactical_helper_explicitly_invoked": True,
        "long_term_and_tactical_layers_separated": True,
        "missing_renderer_fails_closed": True,
        "candidate_runtime_file_count": len(record["candidate_runtime_files_after_integration"]),
        "main_deployment_authorized": False,
        "whole_research_branch_merge_authorized": False,
        "next_decision": record["next_decision"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
