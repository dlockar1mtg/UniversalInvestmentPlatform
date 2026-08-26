from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "unified_decision_terminal_redesign_design.json"

EXPECTED_ID = "METALS-UNIFIED-DECISION-TERMINAL-REDESIGN-DESIGN-1"
EXPECTED_HEAD = "293f149b163f0d9e0f9915f17048eed324b8a6cf"
EXPECTED_DB_SHA = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
EXPECTED_PUBLICATION = "metals-v3-commodity-explanation-r4-20260826"
EXPECTED_FINGERPRINT = "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5"
EXPECTED_RUNTIME_FILES = [
    "foundation/production/dashboard_assets/recommendation_ui.js",
    "foundation/production/dashboard_assets/metals_tactical_ui.js",
    "foundation/production/dashboard_assets/recommendation_visual.css",
]


def all_true(mapping: dict[str, object]) -> bool:
    return bool(mapping) and all(value is True for value in mapping.values())


def main() -> None:
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))

    tactical = design["tactical_presentation_policy"]
    boundaries = design["boundaries"]

    result = {
        "status": "PASS",
        "read_only": True,
        "design_id_bound": design["design_id"] == EXPECTED_ID,
        "source_head_bound": design["source_governed_head"] == EXPECTED_HEAD,
        "database_sha_bound": design["source_database_sha256"] == EXPECTED_DB_SHA,
        "active_r4_bound": design["active_hosted_publication"]["publication_id"] == EXPECTED_PUBLICATION,
        "active_r4_fingerprint_bound": design["active_hosted_publication"]["content_fingerprint"] == EXPECTED_FINGERPRINT,
        "active_r4_count_bound": design["active_hosted_publication"]["record_count"] == 12477,
        "runtime_file_scope_exact": sorted(design["candidate_runtime_files"]) == sorted(EXPECTED_RUNTIME_FILES),
        "current_visual_acceptance_rejected": design["current_visual_acceptance"] == "REJECTED",
        "overview_requirements_all_true": all_true(design["unified_overview_card_requirements"]),
        "decision_summary_requirements_all_true": all_true(design["decision_summary_requirements"]),
        "vehicle_requirements_all_true": all_true(design["vehicle_terminal_requirements"]),
        "gold_requirements_all_true": all_true(design["gold_terminal_requirements"]),
        "uranium_requirements_all_true": all_true(design["uranium_requirements"]),
        "risk_semantics_all_true": all_true({
            key: value
            for key, value in design["risk_semantic_policy"].items()
            if isinstance(value, bool)
        }),
        "forecast_interpretation_all_true": all_true(design["forecast_interpretation_policy"]),
        "acceptance_requirements_all_true": all_true(design["acceptance_requirements"]),
        "neutral_tactical_compact": tactical["NO_TACTICAL_OVERLAY"]["display"] == "compact_status" and tactical["NO_TACTICAL_OVERLAY"]["large_bar_allowed"] is False,
        "supportive_tactical_prominent": tactical["TACTICAL_SUPPORTIVE"]["display"] == "prominent_exception" and tactical["TACTICAL_SUPPORTIVE"]["large_bar_allowed"] is True,
        "defensive_tactical_prominent": tactical["TACTICAL_DEFENSIVE"]["display"] == "prominent_exception" and tactical["TACTICAL_DEFENSIVE"]["large_bar_allowed"] is True,
        "commodity_tactical_compact": tactical["commodity_records"]["display"] == "compact_not_applicable" and tactical["commodity_records"]["large_bar_allowed"] is False,
        "downstream_boundaries_closed": all(value is False for value in boundaries.values()),
        "decision_bound": design["design_decision"] == "APPROVE_METALS_UNIFIED_DECISION_TERMINAL_REDESIGN_FOR_IMPLEMENTATION_AUTHORIZATION_CONSIDERATION",
        "next_decision_bound": design["next_decision"] == "AUTHORIZE_BOUNDED_METALS_UNIFIED_DECISION_TERMINAL_IMPLEMENTATION",
    }

    failed = [key for key, value in result.items() if key not in {"status", "read_only"} and value is not True]
    if failed:
        result["status"] = "FAIL"
        result["failed_checks"] = failed
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(1)

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
