from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "config" / "metals" / "premium_research_ui_implementation_authorization.json"
DESIGN = ROOT / "config" / "metals" / "premium_research_ui_binding_design.json"


def main() -> None:
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    design = json.loads(DESIGN.read_text(encoding="utf-8"))

    contract = auth["implementation_contract"]
    closed = auth["closed_scope"]

    result = {
        "authorization_id_bound": auth["authorization_id"] == "METALS-PREMIUM-RESEARCH-UI-IMPLEMENTATION-AUTHORIZATION-1",
        "source_head_bound": auth["source_governed_head"] == "c7253506d44816b297c470283491da6d0becc732",
        "source_database_bound": auth["source_database_sha256"] == design["source_database_sha256"],
        "active_publication_bound": auth["active_publication_id"] == design["active_publication_id"],
        "active_fingerprint_bound": auth["active_content_fingerprint"] == design["active_content_fingerprint"],
        "design_bound": auth["design_id"] == design["design_id"],
        "ui_change_authorized": contract["recommendation_ui_change_authorized"] is True,
        "test_change_authorized": contract["delivery_test_change_authorized"] is True,
        "premium_overview_bound": contract["metals_overview_must_use_premium_cards"] is True,
        "premium_detail_bound": contract["metals_detail_must_use_premium_research_layout"] is True,
        "final_action_primary": contract["final_action_must_remain_primary"] is True,
        "native_support_only": contract["native_recommendation_must_remain_supporting"] is True,
        "tactical_support_only": contract["tactical_state_must_remain_supporting"] is True,
        "bil_reference_control_bound": contract["bil_must_render_as_reference_control"] is True,
        "no_synthetic_rank": contract["no_synthetic_cross_domain_rank"] is True,
        "no_missing_value_synthesis": contract["no_missing_value_synthesis"] is True,
        "gold_forecast_bound": contract["gold_forecast_horizons_must_remain_3_6_12_24_months"] is True,
        "uranium_unavailability_bound": contract["uranium_unavailable_authority_must_be_explicit"] is True,
        "existing_evidence_only": contract["existing_certified_presentation_records_only"] is True,
        "crypto_preserved": contract["crypto_behavior_must_remain_unchanged"] is True,
        "mtg_preserved": contract["mtg_behavior_must_remain_unchanged"] is True,
        "hosted_writes_closed": closed["hosted_publication_mutation_authorized"] is False,
        "analytical_writes_closed": closed["analytical_database_write_authorized"] is False,
        "recompute_closed": all(closed[key] is False for key in ("model_refresh_authorized", "forecast_refresh_authorized", "recommendation_recompute_authorized", "mtg_premium_recompute_authorized")),
        "manual_deploy_closed": closed["manual_render_deployment_authorized"] is False,
        "execution_closed": closed["automatic_execution_authorized"] is False,
        "decision_bound": auth["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_PREMIUM_RESEARCH_UI_IMPLEMENTATION",
        "next_decision_bound": auth["next_decision"] == "MATERIALIZE_AND_CERTIFY_METALS_PREMIUM_RESEARCH_UI_IMPLEMENTATION",
    }
    result["status"] = "PASS" if all(result.values()) else "FAIL"
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
