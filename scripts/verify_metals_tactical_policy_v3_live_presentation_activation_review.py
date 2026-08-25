from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "config" / "metals" / "tactical_policy_v3_live_presentation_activation_review.json"


def main() -> int:
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    if review["review_id"] != "METALS-TACTICAL-POLICY-V3-LIVE-PRESENTATION-ACTIVATION-REVIEW-1":
        raise RuntimeError("Unexpected review ID.")
    if review["source_authorization_consumed"] is not True:
        raise RuntimeError("Fresh activation authorization was not recorded consumed.")
    active = review["active_publication"]
    if active["publication_id"] != "metals-v3-live-tactical-r2-20260825":
        raise RuntimeError("Unexpected active publication ID.")
    if active["publication_status"] != "ACTIVE":
        raise RuntimeError("Target publication is not ACTIVE.")
    if active["content_fingerprint"] != "21a3e3c8a1e73b7370d23f0704081f7ac01f28609bed22f94d00d4f4c2e7c126":
        raise RuntimeError("Active fingerprint changed.")
    if int(active["record_count"]) != 4181 or int(active["metals_tactical_state_count"]) != 10:
        raise RuntimeError("Active publication counts changed.")
    if int(active["active_pointer_count"]) != 1 or int(active["active_status_count"]) != 1:
        raise RuntimeError("Hosted active-state cardinality changed.")
    if review["previous_publication"]["publication_status"] != "SUPERSEDED":
        raise RuntimeError("Previous publication was not superseded.")
    semantic = review["semantic_state"]
    if semantic["bil_projected_as_opportunity"] is not False:
        raise RuntimeError("BIL entered tactical opportunity projection.")
    if semantic["all_tactical_states"] != "NO_TACTICAL_OVERLAY":
        raise RuntimeError("Tactical state changed.")
    if semantic["all_tactical_regimes"] != "NEUTRAL_OR_UNCERTAIN":
        raise RuntimeError("Tactical regime changed.")
    deployment = review["deployment_state"]
    if deployment["render_configured_branch"] != "main":
        raise RuntimeError("Unexpected Render deployment branch.")
    if deployment["hosted_presentation_data_active"] is not True:
        raise RuntimeError("Hosted presentation data not recorded active.")
    if deployment["metals_tactical_ui_route_present_on_main"] is not False:
        raise RuntimeError("Main UI route state changed.")
    if deployment["metals_tactical_ui_script_present_on_main"] is not False:
        raise RuntimeError("Main UI script state changed.")
    if deployment["visual_dashboard_live_certified"] is not False:
        raise RuntimeError("Visual dashboard prematurely certified live.")
    if review["review_decision"] != "HOSTED_PRESENTATION_ACTIVATION_CERTIFIED_UI_DEPLOYMENT_TO_MAIN_REQUIRED":
        raise RuntimeError("Unexpected review decision.")
    if review["controls"]["activation_may_be_reexecuted"] is not False:
        raise RuntimeError("Consumed activation was incorrectly made reusable.")
    if review["controls"]["main_deployment_may_be_considered"] is not True:
        raise RuntimeError("Main deployment consideration not authorized.")
    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "review_id": review["review_id"],
        "active_publication_id": active["publication_id"],
        "active_content_fingerprint": active["content_fingerprint"],
        "active_record_count": active["record_count"],
        "metals_tactical_state_count": active["metals_tactical_state_count"],
        "previous_publication_status": review["previous_publication"]["publication_status"],
        "render_configured_branch": deployment["render_configured_branch"],
        "hosted_presentation_data_active": True,
        "visual_dashboard_live_certified": False,
        "main_deployment_may_be_considered": True,
        "next_decision": review["next_decision"],
    }, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
