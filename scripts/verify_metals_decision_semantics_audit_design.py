from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "metals" / "decision_semantics_audit_design.json"


def main() -> None:
    design = json.loads(PATH.read_text(encoding="utf-8"))
    required_assets = {
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
    required_columns = {
        "asset_id",
        "asset_kind",
        "native_recommendation",
        "native_recommendation_semantics",
        "uip_normalized_decision",
        "uip_normalization_authority",
        "raw_forecast_horizon_months",
        "raw_expected_return",
        "uncertainty_adjusted_horizon_months",
        "uncertainty_adjusted_expected_return",
        "forecast_conflict_state",
        "risk_semantic_type",
        "risk_value",
        "timing_state",
        "decision_consistency_state",
        "user_facing_primary_status_authorized",
        "user_facing_explanation_required",
    }

    checks = {
        "design_id_bound": design.get("design_id") == "METALS-DECISION-SEMANTICS-AUDIT-DESIGN-1",
        "source_head_bound": design.get("source_governed_head") == "6fdc0a38fda452d291b74da62d96b41703d99f52",
        "visual_acceptance_rejected": design.get("current_visual_acceptance") == "REJECTED",
        "asset_scope_exact": set(design.get("required_asset_scope", [])) == required_assets,
        "audit_columns_complete": required_columns.issubset(set(design.get("required_audit_columns", []))),
        "ranked_mapping_bound": design.get("governed_existing_normalization", {}).get("ranked_opportunity_mapping", {}).get("score_gte_75_and_positive_expected_return") == "STRONG_BUY",
        "bullish_nonpositive_cap_bound": design.get("governed_existing_normalization", {}).get("bullish_native_action_nonpositive_or_missing_forecast_cap") == "WATCH",
        "audit_questions_all_true": all(design.get("audit_questions", {}).values()),
        "fail_closed_rules_all_true": all(design.get("fail_closed_rules", {}).values()),
        "required_outputs_all_true": all(design.get("required_outputs", {}).values()),
        "downstream_boundaries_closed": all(value is False for value in design.get("boundaries", {}).values()),
        "decision_bound": design.get("design_decision") == "APPROVE_METALS_DECISION_SEMANTICS_AUDIT_DESIGN_FOR_READ_ONLY_EXECUTION_AUTHORIZATION_CONSIDERATION",
        "next_decision_bound": design.get("next_decision") == "AUTHORIZE_READ_ONLY_METALS_DECISION_SEMANTICS_AUDIT",
    }

    status = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({"status": status, "read_only": True, **checks}, indent=2, sort_keys=True))
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
