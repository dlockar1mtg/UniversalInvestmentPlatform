from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "comparable_user_facing_decision_layer_design.json"


def main() -> None:
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))

    expected_assets = {
        "metals:commodity:gold",
        "metals:commodity:uranium",
        "metals:vehicle:BIL",
        "metals:vehicle:COPX",
        "metals:vehicle:CPER",
        "metals:vehicle:GLD",
        "metals:vehicle:IAU",
        "metals:vehicle:PPLT",
        "metals:vehicle:SGOL",
        "metals:vehicle:SIVR",
        "metals:vehicle:SLV",
        "metals:vehicle:URA",
    }

    decisions = design["asset_decision_design"]
    conflicted = {
        asset_id
        for asset_id, row in decisions.items()
        if row["primary_user_facing_status"] == "DECISION_CONFLICT"
    }

    safe_hold = {
        asset_id
        for asset_id, row in decisions.items()
        if row["primary_user_facing_status"] == "HOLD"
    }

    checks = {
        "design_id_bound": design["design_id"] == "METALS-COMPARABLE-USER-FACING-DECISION-LAYER-DESIGN-1",
        "source_audit_head_bound": design["source_semantic_audit_head"] == "c103f15a38462e8a3ecbfab24cc87634cd97278e",
        "source_audit_id_bound": design["source_semantic_audit_id"] == "METALS-DECISION-SEMANTICS-AUDIT-EXECUTION-1",
        "database_sha_bound": design["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
        "hosted_r4_bound": (
            design["source_hosted_publication_id"] == "metals-v3-commodity-explanation-r4-20260826"
            and design["source_hosted_fingerprint"] == "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5"
            and design["source_hosted_record_count"] == 12477
        ),
        "audit_counts_bound": design["certified_semantic_audit_counts"] == {
            "asset_count": 12,
            "safe_primary_status_count": 5,
            "blocked_primary_status_count": 7,
            "raw_adjusted_sign_conflict_count": 8,
            "contradiction_count": 17,
        },
        "asset_scope_exact": set(decisions) == expected_assets,
        "gold_hold": decisions["metals:commodity:gold"]["primary_user_facing_status"] == "HOLD",
        "uranium_hold": decisions["metals:commodity:uranium"]["primary_user_facing_status"] == "HOLD",
        "bil_reference_control": decisions["metals:vehicle:BIL"]["primary_user_facing_status"] == "REFERENCE_CONTROL",
        "safe_hold_assets_exact": safe_hold == {
            "metals:commodity:gold",
            "metals:commodity:uranium",
            "metals:vehicle:COPX",
            "metals:vehicle:CPER",
            "metals:vehicle:URA",
        },
        "conflicted_assets_exact": conflicted == {
            "metals:vehicle:GLD",
            "metals:vehicle:IAU",
            "metals:vehicle:PPLT",
            "metals:vehicle:SGOL",
            "metals:vehicle:SIVR",
            "metals:vehicle:SLV",
        },
        "primary_taxonomy_bound": design["primary_decision_taxonomy"] == [
            "STRONG_BUY",
            "BUY",
            "WATCH",
            "HOLD",
            "SELL",
            "STRONG_SELL",
            "DECISION_CONFLICT",
            "REFERENCE_CONTROL",
        ],
        "presentation_rules_all_true": all(design["presentation_rules"].values()),
        "research_rules_all_true": all(design["research_terminal_rules"].values()),
        "fail_closed_rules_all_true": all(design["fail_closed_rules"].values()),
        "candidate_runtime_files_exact": design["candidate_runtime_files"] == [
            "foundation/production/dashboard_assets/recommendation_ui.js",
            "foundation/production/dashboard_assets/metals_tactical_ui.js",
            "foundation/production/dashboard_assets/recommendation_visual.css",
        ],
        "downstream_boundaries_closed": all(value is False for value in design["boundaries"].values()),
        "decision_bound": design["design_decision"] == "APPROVE_METALS_COMPARABLE_USER_FACING_DECISION_LAYER_DESIGN_FOR_IMPLEMENTATION_AUTHORIZATION_CONSIDERATION",
        "next_decision_bound": design["next_decision"] == "AUTHORIZE_BOUNDED_METALS_COMPARABLE_USER_FACING_DECISION_LAYER_IMPLEMENTATION",
    }

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise SystemExit("FAILED: " + ", ".join(failed))

    print(json.dumps({"status": "PASS", "read_only": True, **checks}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
