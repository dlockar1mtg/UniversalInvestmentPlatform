from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONTRACT_PATH = ROOT / "config" / "metals" / "tactical_policy_validation_design.json"

EXPECTED_ELIGIBLE = {
    "metals:vehicle:COPX",
    "metals:vehicle:CPER",
    "metals:vehicle:GLD",
    "metals:vehicle:IAU",
    "metals:vehicle:PPLT",
    "metals:vehicle:SGOL",
    "metals:vehicle:SIVR",
    "metals:vehicle:SLV",
    "metals:vehicle:URA",
    "metals:vehicle:URNM",
}
EXPECTED_POSTURES = {"ACCUMULATE", "HOLD", "WATCH", "REDUCE", "AVOID"}


def main() -> int:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if payload.get("design_id") != "METALS-TACTICAL-POLICY-VALIDATION-DESIGN-1":
        raise RuntimeError("unexpected Metals tactical-policy validation design")
    if payload.get("version") != "1.0.0":
        raise RuntimeError("unsupported Metals tactical-policy validation design version")

    eligible = set(payload.get("eligible_vehicle_asset_ids") or [])
    if eligible != EXPECTED_ELIGIBLE:
        raise RuntimeError("eligible tactical vehicle universe changed")
    references = set(payload.get("reference_control_asset_ids") or [])
    if references != {"metals:vehicle:BIL"}:
        raise RuntimeError("BIL reference/control role changed")
    if eligible & references:
        raise RuntimeError("reference/control asset entered tactical opportunity universe")

    if set(payload.get("candidate_postures") or []) != EXPECTED_POSTURES:
        raise RuntimeError("candidate tactical posture vocabulary changed")

    required = set(payload.get("required_evidence_types") or [])
    if not {"metals_momentum_state", "metals_current_price", "metals_price_history", "recommendation", "risk"}.issubset(required):
        raise RuntimeError("required tactical evidence contract is incomplete")

    semantics = payload.get("semantic_constraints") or {}
    for key in (
        "momentum_state_is_descriptive_not_predictive",
        "forecast_validation_separate_from_policy_validation",
        "missing_evidence_must_remain_missing",
        "reference_control_may_not_receive_opportunity_posture",
        "cross_domain_rank_prohibited",
        "universal_allocation_policy_prohibited",
        "automatic_execution_prohibited",
    ):
        if semantics.get(key) is not True:
            raise RuntimeError(f"required tactical semantic constraint changed: {key}")

    requirements = payload.get("validation_requirements") or {}
    for key in (
        "historical_walk_forward_required",
        "posture_outcomes_must_be_measured_by_horizon",
        "downside_and_drawdown_behavior_must_be_measured",
        "turnover_and_state_churn_must_be_measured",
        "policy_must_be_compared_against_non_tactical_baselines",
        "thresholds_must_be_locked_before_final_validation",
        "no_production_posture_publication_before_validation_pass",
    ):
        if requirements.get(key) is not True:
            raise RuntimeError(f"required tactical validation requirement changed: {key}")

    controls = payload.get("controls") or {}
    if controls.get("validation_design_authorized") is not True:
        raise RuntimeError("tactical-policy validation design is not authorized")
    for key in (
        "policy_execution_authorized",
        "tactical_posture_authorized",
        "presentation_activation_authorized",
        "production_database_write_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
        "missing_authority_may_be_synthesized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited tactical control changed unexpectedly: {key}")

    result = {
        "status": "PASS",
        "read_only": True,
        "design_id": payload["design_id"],
        "eligible_vehicle_count": len(eligible),
        "reference_control_count": len(references),
        "candidate_postures": sorted(EXPECTED_POSTURES),
        "bil_reference_control_verified": True,
        "momentum_descriptive_not_predictive": True,
        "historical_walk_forward_required": True,
        "threshold_lock_required_before_final_validation": True,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "production_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "next_decision": payload["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
