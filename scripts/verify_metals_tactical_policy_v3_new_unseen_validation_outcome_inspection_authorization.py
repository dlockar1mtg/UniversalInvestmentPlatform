from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_new_unseen_validation_outcome_inspection_authorization.json"
FREEZE_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_action_mapping_freeze_decision.json"
REGIME_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_regime_definition_lock_decision.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", required=True)
    args = parser.parse_args()

    package_dir = Path(args.package_dir)
    history_path = package_dir / "metals_v3_new_unseen_validation_history.jsonl"
    coverage_path = package_dir / "coverage.json"
    manifest_path = package_dir / "manifest.json"

    for path in [AUTH_PATH, FREEZE_PATH, REGIME_PATH, history_path, coverage_path, manifest_path]:
        require(path.is_file(), f"required file missing: {path}")

    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    regime = json.loads(REGIME_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))

    require(auth["authorization_id"] == "METALS-TACTICAL-POLICY-V3-NEW-UNSEEN-VALIDATION-OUTCOME-INSPECTION-AUTHORIZATION-1", "unexpected authorization id")
    require(auth["source_regime_definition"] == "METALS-TACTICAL-POLICY-V3-REGIME-DEFINITION-1", "unexpected source regime definition")
    require(auth["source_classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1", "unexpected classifier version")
    require(auth["source_action_mapping_freeze_decision"] == "METALS-TACTICAL-POLICY-V3-ACTION-MAPPING-FREEZE-DECISION-1", "unexpected action freeze")
    require(auth["source_action_mapping_version"] == "METALS-V3-ACTION-MAPPING-1", "unexpected mapping version")

    require(regime["scope_of_lock"]["regime_definition_locked"] is True, "regime definition not locked")
    require(freeze["scope_of_freeze"]["action_mapping_frozen"] is True, "action mapping not frozen")
    require(freeze["scope_of_freeze"]["new_validation_outcome_inspection_authorized"] is False, "source freeze unexpectedly authorized outcome inspection")

    frozen = auth["frozen_unseen_package"]
    require(frozen["package_id"] == "metals-v3-new-unseen-validation-20230822-20260824", "unexpected frozen package id")
    require(frozen["validation_start_date"] == "2023-08-22", "unexpected validation start")
    require(frozen["validation_end_date"] == "2026-08-24", "unexpected validation end")
    require(frozen["row_count"] == 8294, "unexpected frozen row count")
    require(frozen["common_observation_count"] == 754, "unexpected common observation count")
    require(frozen["vehicle_count"] == 11, "unexpected vehicle count")
    require(frozen["opportunity_vehicle_count"] == 10, "unexpected opportunity vehicle count")
    require(frozen["reference_control_vehicle"] == "BIL", "unexpected reference control")
    require(frozen["required_price_semantics"] == "UNADJUSTED_CLOSE", "unexpected price semantics")
    require(frozen["package_frozen"] is True, "package not marked frozen")
    require(frozen["package_outcome_blind_at_freeze"] is True, "package not outcome blind at freeze")

    actual_history_sha = sha256(history_path)
    actual_coverage_sha = sha256(coverage_path)
    actual_manifest_sha = sha256(manifest_path)
    require(actual_history_sha == frozen["history_sha256"], "history sha mismatch")
    require(actual_coverage_sha == frozen["coverage_sha256"], "coverage sha mismatch")
    require(actual_manifest_sha == frozen["manifest_sha256"], "manifest sha mismatch")

    require(manifest["package_id"] == frozen["package_id"], "manifest package id mismatch")
    require(manifest["package_frozen"] is True, "manifest package not frozen")
    require(manifest["outcome_blind"] is True, "manifest package not outcome blind")
    require(manifest["classifier_executed"] is False, "classifier was already executed")
    require(manifest["validation_outcomes_calculated"] is False, "outcomes were already calculated")
    require(manifest["validation_outcomes_inspected"] is False, "outcomes were already inspected")
    require(manifest["history_sha256"] == actual_history_sha, "manifest history hash mismatch")
    require(manifest["coverage_sha256"] == actual_coverage_sha, "manifest coverage hash mismatch")

    require(coverage["package_id"] == frozen["package_id"], "coverage package id mismatch")
    require(coverage["row_count"] == frozen["row_count"], "coverage row count mismatch")
    require(coverage["common_observation_count"] == frozen["common_observation_count"], "coverage common observation mismatch")

    warmup = auth["point_in_time_warmup_authority"]
    require(warmup["package_id"] == "metals-v2-validation-history-20191204-20230821", "unexpected warmup package")
    require(warmup["warmup_end_date"] == "2023-08-21", "unexpected warmup end")
    require(warmup["may_be_used_only_for_point_in_time_feature_warmup"] is True, "warmup scope changed")
    require(warmup["warmup_rows_may_not_be_validation_label_rows"] is True, "warmup rows may become labels")
    require(warmup["warmup_rows_may_not_be_validation_outcome_rows"] is True, "warmup rows may become outcomes")
    require(warmup["v1_v2_intervals_remain_consumed"] is True, "consumed interval protection changed")

    seq = auth["authorized_execution_sequence"]
    for key in [
        "step_1_verify_all_frozen_input_hashes",
        "step_2_construct_point_in_time_features_using_only_information_available_through_each_label_date",
        "step_3_assign_locked_regime_labels_only_on_or_after_2023_08_22",
        "step_4_apply_frozen_action_mapping",
        "step_5_persist_and_hash_label_ledger_before_forward_outcome_calculation",
        "step_6_calculate_predeclared_forward_outcomes_from_frozen_history",
        "step_7_evaluate_locked_primary_and_secondary_validation_checks",
        "label_ledger_may_not_change_after_forward_outcomes_are_calculated",
    ]:
        require(seq[key] is True, f"missing execution sequence control: {key}")
    require(seq["network_query_during_execution_authorized"] is False, "network query unexpectedly authorized")
    require(seq["source_data_refresh_during_execution_authorized"] is False, "source refresh unexpectedly authorized")

    protocol = auth["locked_validation_protocol"]
    require(protocol["primary_horizon_trading_days"] == 63, "primary horizon changed")
    require(protocol["secondary_horizons_trading_days"] == [21, 126], "secondary horizons changed")
    require(protocol["minimum_compared_group_support"] == 20, "support floor changed")
    require(protocol["minimum_distinct_exposure_families_per_directional_state"] == 2, "family floor changed")
    require(protocol["all_three_primary_directional_checks_required"] is True, "primary checks changed")
    require(protocol["secondary_horizons_cannot_substitute_for_primary_failure"] is True, "secondary rescue unexpectedly allowed")
    require(protocol["insufficient_primary_support_is_fail_closed"] is True, "support failure not fail closed")

    controls = auth["controls"]
    require(controls["new_validation_package_frozen"] is True, "package freeze control false")
    require(controls["new_validation_outcome_inspection_authorized"] is True, "outcome inspection not authorized")
    require(controls["new_validation_result_authorized"] is True, "validation result not authorized")
    require(controls["network_collection_authorized"] is False, "network collection unexpectedly authorized")
    require(controls["source_refresh_authorized"] is False, "source refresh unexpectedly authorized")
    require(controls["live_tactical_posture_authorized"] is False, "live tactical posture unexpectedly authorized")
    require(controls["presentation_activation_authorized"] is False, "presentation unexpectedly authorized")
    require(controls["production_database_write_authorized"] is False, "database write unexpectedly authorized")
    require(controls["model_retraining_authorized"] is False, "model retraining unexpectedly authorized")

    require(auth["next_decision"] == "EXECUTE_METALS_TACTICAL_POLICY_V3_NEW_UNSEEN_VALIDATION_OUTCOME_INSPECTION", "unexpected next decision")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "authorization_id": auth["authorization_id"],
        "package_id": frozen["package_id"],
        "history_sha256": actual_history_sha,
        "coverage_sha256": actual_coverage_sha,
        "manifest_sha256": actual_manifest_sha,
        "row_count": frozen["row_count"],
        "common_observation_count": frozen["common_observation_count"],
        "validation_start_date": frozen["validation_start_date"],
        "validation_end_date": frozen["validation_end_date"],
        "primary_validation_horizon_trading_days": protocol["primary_horizon_trading_days"],
        "minimum_support_floor": protocol["minimum_compared_group_support"],
        "minimum_exposure_family_count": protocol["minimum_distinct_exposure_families_per_directional_state"],
        "outcome_inspection_authorized": controls["new_validation_outcome_inspection_authorized"],
        "validation_result_authorized": controls["new_validation_result_authorized"],
        "network_collection_authorized": controls["network_collection_authorized"],
        "tactical_posture_authorized": controls["live_tactical_posture_authorized"],
        "production_database_write_executed": False,
        "presentation_activation_executed": False,
        "next_decision": auth["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
