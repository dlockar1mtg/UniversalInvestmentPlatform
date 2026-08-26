from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "r4_presentation_hierarchy_recovery_design.json"

EXPECTED_SOURCE_HEAD = "84241cf16c452c58e35e64cbcb811057d11ec060"
EXPECTED_DB_SHA = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
EXPECTED_PUBLICATION = "metals-v3-commodity-explanation-r4-20260826"
EXPECTED_FINGERPRINT = "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5"
EXPECTED_RUNTIME_FILES = [
    "foundation/production/dashboard_assets/recommendation_ui.js",
    "foundation/production/dashboard_assets/metals_tactical_ui.js",
    "foundation/production/dashboard_assets/recommendation_visual.css",
]


def main() -> int:
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))

    checks = {
        "design_id_bound": design.get("design_id") == "METALS-r4-PRESENTATION-HIERARCHY-RECOVERY-DESIGN-1",
        "source_head_bound": design.get("source_governed_head") == EXPECTED_SOURCE_HEAD,
        "database_sha_bound": design.get("source_database_sha256") == EXPECTED_DB_SHA,
        "active_r4_bound": design.get("active_hosted_publication", {}).get("publication_id") == EXPECTED_PUBLICATION,
        "active_r4_fingerprint_bound": design.get("active_hosted_publication", {}).get("content_fingerprint") == EXPECTED_FINGERPRINT,
        "active_r4_count_bound": int(design.get("active_hosted_publication", {}).get("record_count", -1)) == 12477,
        "runtime_file_scope_exact": sorted(design.get("candidate_runtime_files", [])) == sorted(EXPECTED_RUNTIME_FILES),
        "gold_primary_surfaces_complete": set(design.get("gold_required_primary_surfaces", {})) == {
            "hero_summary",
            "hero_risk_context",
            "why_this_recommendation",
            "risk_summary",
            "risk_assessment",
            "overview_card",
            "secondary_table",
        },
        "gold_semantic_guardrails_all_true": bool(design.get("gold_semantic_guardrails")) and all(design["gold_semantic_guardrails"].values()),
        "uranium_behavior_all_true": bool(design.get("uranium_required_behavior")) and all(design["uranium_required_behavior"].values()),
        "visual_hierarchy_requirements_all_true": bool(design.get("visual_hierarchy_requirements")) and all(design["visual_hierarchy_requirements"].values()),
        "acceptance_requirements_all_true": bool(design.get("acceptance_requirements")) and all(design["acceptance_requirements"].values()),
        "downstream_boundaries_closed": bool(design.get("boundaries")) and not any(design["boundaries"].values()),
        "decision_bound": design.get("design_decision") == "APPROVE_METALS_r4_PRESENTATION_HIERARCHY_RECOVERY_DESIGN_FOR_IMPLEMENTATION_AUTHORIZATION_CONSIDERATION",
        "next_decision_bound": design.get("next_decision") == "AUTHORIZE_BOUNDED_METALS_r4_PRESENTATION_HIERARCHY_RECOVERY_IMPLEMENTATION",
    }

    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "read_only": True,
        **checks,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
