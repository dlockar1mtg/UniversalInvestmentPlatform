from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "premium_research_ui_binding_design.json"

EXPECTED_SOURCE_HEAD = "40c8f19507c44d44e433dc6835a774858f81e791"
EXPECTED_ACTIVE = "metals-mtg-composite-recovery-r1-20260828"
EXPECTED_FINGERPRINT = "67352221b51e7479fe9e154e12dd718a9cf392c794d2320461203fe980bfc009"
EXPECTED_DB_SHA = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def main() -> None:
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8-sig"))

    result = {
        "design_id_bound": design.get("design_id") == "METALS-PREMIUM-RESEARCH-UI-BINDING-DESIGN-1",
        "source_head_bound": design.get("source_governed_head") == EXPECTED_SOURCE_HEAD,
        "active_publication_bound": design.get("active_publication_id") == EXPECTED_ACTIVE,
        "active_fingerprint_bound": design.get("active_content_fingerprint") == EXPECTED_FINGERPRINT,
        "source_database_bound": design.get("source_database_sha256") == EXPECTED_DB_SHA,
        "existing_evidence_only": design.get("evidence_basis") == "EXISTING_HOSTED_CERTIFIED_PRESENTATION_RECORDS_ONLY",
        "final_action_primary": design.get("semantic_guards", {}).get("final_action_is_only_primary_action") is True,
        "native_support_only": design.get("semantic_guards", {}).get("native_recommendation_is_supporting_evidence_only") is True,
        "tactical_support_only": design.get("semantic_guards", {}).get("tactical_state_never_replaces_final_action") is True,
        "no_synthetic_rank": design.get("semantic_guards", {}).get("cross_domain_rank_prohibited") is True,
        "no_missing_value_synthesis": design.get("semantic_guards", {}).get("missing_values_must_not_be_synthesized") is True,
        "bil_reference_control_bound": design.get("overview_design", {}).get("reference_control_handling") == "BIL_MUST_RENDER_AS_REFERENCE_CONTROL_NOT_INVESTMENT_OPPORTUNITY",
        "gold_forecast_bound": design.get("binding_inventory", {}).get("gold_commodity", {}).get("forecast_horizons_months") == [3, 6, 12, 24],
        "uranium_unavailability_bound": design.get("binding_inventory", {}).get("uranium_commodity", {}).get("availability_reason") == "NO_CURRENT_COMMODITY_FORECAST_MODEL_OR_REGIME_AUTHORITY",
        "implementation_closed": all(
            design.get("implementation_scope", {}).get(key) is False
            for key in (
                "recommendation_ui_change_authorized",
                "delivery_test_change_authorized",
                "hosted_publication_mutation_authorized",
                "analytical_database_write_authorized",
                "model_refresh_authorized",
                "forecast_refresh_authorized",
                "recommendation_recompute_authorized",
                "manual_render_deployment_authorized",
            )
        ),
        "decision_bound": design.get("design_decision") == "AUTHORIZE_BOUNDED_METALS_PREMIUM_RESEARCH_UI_IMPLEMENTATION_DESIGN",
        "next_decision_bound": design.get("next_decision") == "CERTIFY_METALS_PREMIUM_RESEARCH_UI_BINDING_DESIGN_AND_AUTHORIZE_IMPLEMENTATION",
    }

    result["status"] = "PASS" if all(result.values()) else "FAIL"
    print(json.dumps(result, indent=2, sort_keys=True))

    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
