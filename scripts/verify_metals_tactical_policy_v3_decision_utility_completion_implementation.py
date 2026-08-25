from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_PATH = ROOT / "config/metals/tactical_policy_v3_decision_utility_completion_implementation.json"
PROJECTION_PATH = ROOT / "foundation/presentation/metals_tactical_projection.py"
EXTENSION_PATH = ROOT / "config/presentation/dash_read_1_metals_tactical_extension.json"
TACTICAL_UI_PATH = ROOT / "foundation/production/dashboard_assets/metals_tactical_ui.js"
RECOMMENDATION_UI_PATH = ROOT / "foundation/production/dashboard_assets/recommendation_ui.js"


def main() -> None:
    implementation = json.loads(IMPLEMENTATION_PATH.read_text(encoding="utf-8"))
    extension = json.loads(EXTENSION_PATH.read_text(encoding="utf-8"))
    projection = PROJECTION_PATH.read_text(encoding="utf-8")
    tactical_ui = TACTICAL_UI_PATH.read_text(encoding="utf-8")

    runtime_files = implementation.get("runtime_files_changed") or []
    behavior = implementation.get("implemented_behavior") or {}
    guardrails = implementation.get("semantic_guardrails") or {}
    boundaries = implementation.get("boundaries") or {}

    result = {
        "status": "PASS",
        "read_only": True,
        "implementation_id": implementation.get("implementation_id"),
        "runtime_file_count": len(runtime_files),
        "shared_recommendation_ui_unchanged_by_design": implementation.get("authorized_file_deliberately_unchanged") == "foundation/production/dashboard_assets/recommendation_ui.js",
        "current_price_projection_present": "metals_current_price" in projection and "current_price_usd" in projection,
        "price_history_projection_present": "metals_price_history" in projection and "close_usd" in projection,
        "external_hash_lock_present": "EXPECTED_CURRENT_PRICE_SHA256" in projection and "EXPECTED_PRICE_HISTORY_SHA256" in projection and "EXPECTED_MANIFEST_SHA256" in projection,
        "unadjusted_close_locked": extension.get("external_price_package", {}).get("price_semantics") == "UNADJUSTED_CLOSE" and "UNADJUSTED_CLOSE" in tactical_ui,
        "current_price_ui_present": "Current price" in tactical_ui and "Price as of" in tactical_ui,
        "price_history_chart_present": "Historical market price" in tactical_ui and "metals-price-history-panel" in tactical_ui,
        "raw_adjusted_return_distinction_present": "Raw expected return" in tactical_ui and "Adjusted return" in tactical_ui,
        "recommendation_change_evidence_promoted": "Recommendation-change evidence:" in tactical_ui,
        "contradictory_empty_forecast_repaired": "Certified vehicle return forecasts are available below" in tactical_ui,
        "uranium_missing_forecast_explicit": "No standard commodity forecast is currently available for Uranium" in tactical_ui,
        "commodity_price_not_inferred": guardrails.get("commodity_price_not_inferred_from_vehicle_price") is True,
        "unsupported_fields_preserved": all(guardrails.values()),
        "analytical_database_write_authorized": boundaries.get("analytical_database_write_authorized"),
        "hosted_publication_write_authorized": boundaries.get("hosted_publication_write_authorized"),
        "main_deployment_authorized": boundaries.get("main_deployment_authorized"),
        "next_decision": implementation.get("next_decision"),
    }

    required_true = [
        "shared_recommendation_ui_unchanged_by_design",
        "current_price_projection_present",
        "price_history_projection_present",
        "external_hash_lock_present",
        "unadjusted_close_locked",
        "current_price_ui_present",
        "price_history_chart_present",
        "raw_adjusted_return_distinction_present",
        "recommendation_change_evidence_promoted",
        "contradictory_empty_forecast_repaired",
        "uranium_missing_forecast_explicit",
        "commodity_price_not_inferred",
        "unsupported_fields_preserved",
    ]
    if implementation.get("implementation_id") != "METALS-TACTICAL-POLICY-V3-DECISION-UTILITY-COMPLETION-IMPLEMENTATION-1":
        result["status"] = "FAIL"
    if len(runtime_files) != 3:
        result["status"] = "FAIL"
    if not all(result[name] is True for name in required_true):
        result["status"] = "FAIL"
    if any(boundaries.get(name) is not False for name in boundaries):
        result["status"] = "FAIL"
    if implementation.get("next_decision") != "CERTIFY_METALS_DECISION_UTILITY_COMPLETION_AND_LOCAL_PUBLICATION_PROJECTION":
        result["status"] = "FAIL"

    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
