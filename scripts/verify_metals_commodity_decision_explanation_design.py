from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "commodity_decision_explanation_design.json"

EXPECTED_DESIGN_ID = "METALS-COMMODITY-DECISION-EXPLANATION-DESIGN-1"
EXPECTED_SOURCE_HEAD = "265ed5776149edfcc42e5d7b08c0fdfe86e6a6b4"
EXPECTED_DB_SHA = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
EXPECTED_RECORD_TYPE = "metals_commodity_decision_explanation"
EXPECTED_FILES = [
    "foundation/presentation/metals_tactical_projection.py",
    "config/presentation/dash_read_1_metals_tactical_extension.json",
    "foundation/production/dashboard_assets/metals_tactical_ui.js",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))

    require(design["design_id"] == EXPECTED_DESIGN_ID, "Unexpected design ID")
    require(design["source_governed_head"] == EXPECTED_SOURCE_HEAD, "Source HEAD changed")
    require(design["source_database_sha256"] == EXPECTED_DB_SHA, "Database SHA binding changed")
    require(design["new_record_type"] == EXPECTED_RECORD_TYPE, "Derived record type changed")

    findings = design["source_audit_findings"]
    require(findings["gold_native_rationale_present"] is False, "Gold native rationale finding changed")
    require(findings["gold_native_risk_summary_present"] is False, "Gold native risk summary finding changed")
    require(findings["gold_current_typed_risk_present"] is False, "Gold typed risk finding changed")
    require(findings["gold_historical_typed_risk_present"] is False, "Gold historical risk finding changed")
    require(findings["gold_recommendation_change_present"] is False, "Gold recommendation-change finding changed")
    require(findings["gold_current_forecast_present"] is True, "Gold forecast authority disappeared")
    require(findings["gold_current_model_components_present"] is True, "Gold model-component authority disappeared")
    require(findings["gold_current_regime_probabilities_present"] is True, "Gold regime authority disappeared")
    require(findings["uranium_current_forecast_present"] is False, "Uranium forecast finding changed")
    require(findings["uranium_current_model_components_present"] is False, "Uranium model finding changed")
    require(findings["uranium_current_regime_probabilities_present"] is False, "Uranium regime finding changed")
    require(findings["gld_current_typed_risk_present"] is True, "GLD typed risk comparison disappeared")
    require(findings["ura_current_typed_risk_present"] is True, "URA typed risk comparison disappeared")

    semantics = design["authority_semantics"]
    require(all(value is True for value in semantics.values()), "One or more semantic guardrails are not enabled")

    gold = design["gold"]
    require(gold["eligible_for_derived_rationale"] is True, "Gold rationale eligibility changed")
    require(gold["eligible_for_forecast_regime_risk_context"] is True, "Gold risk-context eligibility changed")
    require(gold["required_forecast_horizons_months"] == [3, 6, 12, 24], "Gold forecast horizons changed")
    require(gold["forecast_regime_risk_context_rules"]["semantic_label"] == "Forecast / regime risk context", "Risk-context semantic label changed")
    require(gold["forecast_regime_risk_context_rules"]["must_not_map_to_LOW_MEDIUM_HIGH_native_risk_levels"] is True, "Native risk mapping guardrail disabled")

    uranium = design["uranium"]
    require(uranium["eligible_for_derived_rationale"] is False, "Uranium must remain ineligible for derived rationale")
    require(uranium["eligible_for_forecast_regime_risk_context"] is False, "Uranium must remain ineligible for derived risk context")
    require(uranium["required_presentation_state"]["must_not_infer_from_URA"] is True, "URA inference guardrail disabled")
    require(uranium["required_presentation_state"]["must_not_infer_from_URNM"] is True, "URNM inference guardrail disabled")

    require(sorted(design["candidate_implementation_files"]) == sorted(EXPECTED_FILES), "Candidate implementation file scope changed")
    require(all(value is False for value in design["boundaries"].values()), "A downstream authorization boundary is unexpectedly enabled")
    require(design["design_decision"] == "APPROVE_METALS_COMMODITY_DECISION_EXPLANATION_DESIGN_FOR_IMPLEMENTATION_CONSIDERATION", "Unexpected design decision")
    require(design["next_decision"] == "AUTHORIZE_METALS_COMMODITY_DECISION_EXPLANATION_IMPLEMENTATION", "Unexpected next decision")

    result = {
        "status": "PASS",
        "read_only": True,
        "design_id": design["design_id"],
        "source_head_bound": True,
        "database_sha_bound": True,
        "gold_derived_rationale_allowed": True,
        "gold_forecast_regime_risk_context_allowed": True,
        "gold_native_risk_not_fabricated": True,
        "gold_vehicle_risk_not_inherited": True,
        "uranium_derived_explanation_blocked": True,
        "uranium_vehicle_inference_blocked": True,
        "candidate_file_scope_exact": True,
        "downstream_authority_all_false": True,
        "next_decision": design["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
