from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "config" / "metals" / "tactical_policy_v3_main_deployment_readiness_review.json"
READ_API = ROOT / "foundation" / "presentation" / "read_api.py"
TACTICAL_UI = ROOT / "foundation" / "production" / "dashboard_assets" / "metals_tactical_ui.js"
RECOMMENDATION_UI = ROOT / "foundation" / "production" / "dashboard_assets" / "recommendation_ui.js"


def main() -> int:
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    read_api = READ_API.read_text(encoding="utf-8")
    tactical_ui = TACTICAL_UI.read_text(encoding="utf-8")
    recommendation_ui = RECOMMENDATION_UI.read_text(encoding="utf-8")

    if review["review_id"] != "METALS-TACTICAL-POLICY-V3-MAIN-DEPLOYMENT-READINESS-REVIEW-1":
        raise RuntimeError("Unexpected main deployment readiness review ID.")
    if review["readiness_decision"] != "NOT_READY_REQUIRES_EXPLICIT_RECOMMENDATION_UI_TACTICAL_INTEGRATION":
        raise RuntimeError("Unexpected main deployment readiness decision.")
    if review["main_deployment_authorized"] is not False:
        raise RuntimeError("Main deployment was prematurely authorized.")
    if review["whole_research_branch_merge_authorized"] is not False:
        raise RuntimeError("Whole research branch merge was prematurely authorized.")
    if "SELECT record_type, record_key, payload_json" not in read_api:
        raise RuntimeError("Asset-detail API no longer returns arbitrary record types.")
    if 'const RECORD_TYPE="tactical_state"' not in tactical_ui:
        raise RuntimeError("Metals tactical helper is missing tactical-state semantics.")
    if "renderTacticalPanel" not in tactical_ui:
        raise RuntimeError("Metals tactical helper no longer provides a rendering entry point.")
    if "UIPMetalsTactical.renderTacticalPanel" in recommendation_ui:
        raise RuntimeError("Recommendation UI is already integrated; readiness review is stale.")
    if review["presentation_readiness"]["recommendation_ui_explicitly_invokes_tactical_panel"] is not False:
        raise RuntimeError("Recommendation UI integration state is incorrectly recorded.")
    if review["next_decision"] != "IMPLEMENT_METALS_V3_RECOMMENDATION_UI_TACTICAL_INTEGRATION":
        raise RuntimeError("Unexpected next decision.")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "review_id": review["review_id"],
        "readiness_decision": review["readiness_decision"],
        "main_deployment_authorized": review["main_deployment_authorized"],
        "whole_research_branch_merge_authorized": review["whole_research_branch_merge_authorized"],
        "asset_detail_supports_tactical_state_without_new_read_api": True,
        "tactical_helper_render_entry_point_present": True,
        "recommendation_ui_tactical_integration_present": False,
        "bounded_candidate_deployment_file_count": len(review["bounded_candidate_deployment_files"]),
        "next_decision": review["next_decision"],
    }, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
