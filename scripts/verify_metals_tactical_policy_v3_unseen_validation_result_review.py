from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_unseen_validation_result_review.json"

EXPECTED_EXECUTION_ID = "METALS-TACTICAL-POLICY-V3-NEW-UNSEEN-VALIDATION-OUTCOME-INSPECTION-1"
EXPECTED_REVIEW_ID = "METALS-TACTICAL-POLICY-V3-UNSEEN-VALIDATION-RESULT-REVIEW-1"
EXPECTED_LABEL_SHA = "1f543a8a4b570a042289a098fc8e4cae06b3c43a553fd7c1000bb6a50bed4ae9"
EXPECTED_OUTCOME_SHA = "f687cf33d41d4235a1bd735b3c79fdf22fa7b0ce01c16e8c36c3714ac097e429"
EXPECTED_RESULT_SHA = "a4e0d27aa3e994f92570e6fccf7e88edde0f205da647ddd2d8a6d970173de663"
EXPECTED_MANIFEST_SHA = "aa698df5e191f91504608644e8be2f568f8f6f57c13b56a836c5d24311221965"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-dir", required=True)
    args = parser.parse_args()

    execution_dir = Path(args.execution_dir).resolve()
    require(execution_dir.is_dir(), "execution directory is missing")

    label_path = execution_dir / "unseen_label_ledger.csv"
    outcome_path = execution_dir / "unseen_outcome_ledger.csv"
    result_path = execution_dir / "validation_result.json"
    manifest_path = execution_dir / "manifest.json"

    for path in [label_path, outcome_path, result_path, manifest_path]:
        require(path.is_file(), f"required execution artifact missing: {path.name}")

    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    require(review["review_id"] == EXPECTED_REVIEW_ID, "unexpected review id")
    require(review["source_execution_id"] == EXPECTED_EXECUTION_ID, "unexpected source execution")
    require(manifest["execution_id"] == EXPECTED_EXECUTION_ID, "persisted execution id changed")

    hashes = review["source_execution_artifacts"]
    require(hashes["label_ledger_sha256"] == EXPECTED_LABEL_SHA, "review label hash changed")
    require(hashes["outcome_ledger_sha256"] == EXPECTED_OUTCOME_SHA, "review outcome hash changed")
    require(hashes["validation_result_sha256"] == EXPECTED_RESULT_SHA, "review result hash changed")
    require(hashes["execution_manifest_sha256"] == EXPECTED_MANIFEST_SHA, "review manifest hash changed")

    require(sha256_file(label_path) == EXPECTED_LABEL_SHA, "persisted label ledger hash mismatch")
    require(sha256_file(outcome_path) == EXPECTED_OUTCOME_SHA, "persisted outcome ledger hash mismatch")
    require(sha256_file(result_path) == EXPECTED_RESULT_SHA, "persisted validation result hash mismatch")
    require(sha256_file(manifest_path) == EXPECTED_MANIFEST_SHA, "persisted execution manifest hash mismatch")

    governed = review["governed_validation_result"]
    require(governed["validation_result"] == "PASS", "review does not preserve PASS result")
    require(governed["primary_horizon_trading_days"] == 63, "primary horizon changed")
    require(governed["primary_support_gate_met"] is True, "primary support gate not preserved")
    require(governed["primary_exposure_family_gate_met"] is True, "primary family gate not preserved")
    require(governed["all_three_primary_directional_checks_met"] is True, "primary directional checks not preserved")
    require(governed["supportive_63d_observation_count"] == 801, "supportive support changed")
    require(governed["defensive_63d_observation_count"] == 1152, "defensive support changed")
    require(governed["supportive_63d_exposure_family_count"] == 7, "supportive family breadth changed")
    require(governed["defensive_63d_exposure_family_count"] == 7, "defensive family breadth changed")
    require(governed["minimum_compared_group_support"] == 20, "support floor changed")
    require(governed["minimum_distinct_exposure_families_per_directional_state"] == 2, "family floor changed")
    require(governed["secondary_horizons_cannot_substitute_for_primary_failure"] is True, "secondary rescue boundary changed")

    require(result["validation_result"] == "PASS", "persisted result is not PASS")
    require(result["primary_horizon_trading_days"] == 63, "persisted primary horizon changed")
    require(result["primary_support_gate_met"] is True, "persisted support gate failed")
    require(result["primary_exposure_family_gate_met"] is True, "persisted family gate failed")
    require(result["all_three_primary_directional_checks_met"] is True, "persisted directional checks failed")
    require(result["supportive_63d_observation_count"] == 801, "persisted supportive count changed")
    require(result["defensive_63d_observation_count"] == 1152, "persisted defensive count changed")
    require(result["supportive_63d_exposure_family_count"] == 7, "persisted supportive family count changed")
    require(result["defensive_63d_exposure_family_count"] == 7, "persisted defensive family count changed")
    require(result["label_ledger_hashed_before_outcome_calculation"] is True, "label hash boundary failed")
    require(result["v2_history_used_only_for_point_in_time_warmup"] is True, "V2 warmup boundary failed")
    require(result["v2_rows_entered_new_validation_labels_or_outcomes"] is False, "consumed V2 rows entered unseen validation")
    require(result["tactical_posture_authorized"] is False, "persisted result unexpectedly authorizes tactical posture")

    findings = review["review_findings"]
    for key in [
        "genuinely_unseen_validation_completed",
        "locked_classifier_was_used",
        "frozen_action_mapping_was_used",
        "label_ledger_was_hashed_before_forward_outcome_calculation",
        "consumed_v2_history_was_used_only_for_point_in_time_warmup",
        "primary_validation_support_was_sufficient",
        "primary_validation_exposure_family_breadth_was_sufficient",
        "all_three_locked_primary_directional_checks_passed",
        "v3_tactical_policy_cleared_unseen_validation",
        "validation_pass_does_not_itself_authorize_live_tactical_posture",
        "classifier_or_mapping_may_not_be_retuned_on_consumed_unseen_interval",
        "unseen_interval_is_consumed_for_future_validation",
    ]:
        require(findings[key] is True, f"review finding missing: {key}")
    require(findings["consumed_v2_rows_entered_new_validation_labels_or_outcomes"] is False, "review consumed-evidence boundary changed")

    require(review["review_decision"] == "VALIDATION_PASS_CONFIRMED_FOR_POST_VALIDATION_LIVE_USE_CONSIDERATION", "unexpected review decision")

    controls = review["controls"]
    require(controls["v3_unseen_validation_pass_certified"] is True, "PASS not certified")
    require(controls["v3_tactical_policy_validated_for_live_use_consideration"] is True, "live-use consideration not authorized")
    for key in [
        "candidate_tactical_posture_authorized",
        "live_tactical_posture_authorized",
        "presentation_activation_authorized",
        "production_database_write_authorized",
        "native_source_query_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ]:
        require(controls[key] is False, f"unexpected downstream authorization: {key}")

    require(review["next_decision"] == "DESIGN_METALS_TACTICAL_POLICY_V3_POST_VALIDATION_LIVE_USE_AUTHORIZATION", "unexpected next decision")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "review_id": review["review_id"],
        "validation_result": governed["validation_result"],
        "primary_horizon_trading_days": governed["primary_horizon_trading_days"],
        "primary_support_gate_met": governed["primary_support_gate_met"],
        "primary_exposure_family_gate_met": governed["primary_exposure_family_gate_met"],
        "all_three_primary_directional_checks_met": governed["all_three_primary_directional_checks_met"],
        "supportive_63d_observation_count": governed["supportive_63d_observation_count"],
        "defensive_63d_observation_count": governed["defensive_63d_observation_count"],
        "supportive_63d_exposure_family_count": governed["supportive_63d_exposure_family_count"],
        "defensive_63d_exposure_family_count": governed["defensive_63d_exposure_family_count"],
        "validated_for_live_use_consideration": controls["v3_tactical_policy_validated_for_live_use_consideration"],
        "live_tactical_posture_authorized": controls["live_tactical_posture_authorized"],
        "production_database_write_executed": False,
        "presentation_activation_executed": False,
        "next_decision": review["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
