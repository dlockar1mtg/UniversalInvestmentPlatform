from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_EXECUTION_ID = "METALS-TACTICAL-POLICY-V3-NEW-UNSEEN-VALIDATION-OUTCOME-INSPECTION-1"
EXPECTED_AUTHORIZATION_ID = "METALS-TACTICAL-POLICY-V3-NEW-UNSEEN-VALIDATION-OUTCOME-INSPECTION-AUTHORIZATION-1"
EXPECTED_PACKAGE_ID = "metals-v3-new-unseen-validation-20230822-20260824"
EXPECTED_UNSEEN_HISTORY_SHA = "597a979ad5b5c031b4c15b84e3d8b23389c780e9a3fc5a19bd1b06ca4b61a6d5"
EXPECTED_UNSEEN_COVERAGE_SHA = "3de3cb2d21ff247f78e210372bc5505bf13d5b3fd2475260fc84cfb514d91c7e"
EXPECTED_UNSEEN_MANIFEST_SHA = "69ed6ff5324f148734a8b84e672e028fcd2e17893bfac4b4c402063916dcf205"
EXPECTED_V2_HISTORY_SHA = "400aa5792533653eccf7bdfb3dd4b67fddb8f45ad138bda1a7d4ac1c1137bd62"
ACTION_MAP = {
    "TREND_PERSISTENCE": "TACTICAL_SUPPORTIVE",
    "MEAN_REVERSION_OR_EXHAUSTION": "TACTICAL_DEFENSIVE",
    "NEUTRAL_OR_UNCERTAIN": "NO_TACTICAL_OVERLAY",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    root = Path(args.output_dir).resolve()
    require(root.is_dir(), "execution output directory is missing")

    manifest_path = root / "manifest.json"
    label_path = root / "unseen_label_ledger.csv"
    outcome_path = root / "unseen_outcome_ledger.csv"
    result_path = root / "validation_result.json"
    for path in [manifest_path, label_path, outcome_path, result_path]:
        require(path.is_file(), f"required execution artifact missing: {path.name}")

    manifest = load_json(manifest_path)
    result = load_json(result_path)
    labels = load_csv(label_path)
    outcomes = load_csv(outcome_path)

    require(manifest["execution_id"] == EXPECTED_EXECUTION_ID, "unexpected execution id")
    require(manifest["authorization_id"] == EXPECTED_AUTHORIZATION_ID, "unexpected authorization id")
    require(manifest["package_id"] == EXPECTED_PACKAGE_ID, "unexpected package id")
    require(manifest["unseen_history_sha256"] == EXPECTED_UNSEEN_HISTORY_SHA, "unseen history authority changed")
    require(manifest["unseen_coverage_sha256"] == EXPECTED_UNSEEN_COVERAGE_SHA, "unseen coverage authority changed")
    require(manifest["unseen_manifest_sha256"] == EXPECTED_UNSEEN_MANIFEST_SHA, "unseen manifest authority changed")
    require(manifest["v2_warmup_history_sha256"] == EXPECTED_V2_HISTORY_SHA, "V2 warmup authority changed")
    require(manifest["label_ledger_sha256"] == sha256_file(label_path), "label ledger hash mismatch")
    require(manifest["outcome_ledger_sha256"] == sha256_file(outcome_path), "outcome ledger hash mismatch")
    require(manifest["validation_result_sha256"] == sha256_file(result_path), "validation result hash mismatch")
    require(manifest["network_collection_executed"] is False, "network collection unexpectedly executed")
    require(manifest["production_database_write_executed"] is False, "database write unexpectedly executed")
    require(manifest["presentation_activation_executed"] is False, "presentation unexpectedly activated")
    require(manifest["tactical_posture_authorized"] is False, "tactical posture unexpectedly authorized")
    require(manifest["execution_consumed_once"] is True, "execution consumption control missing")

    require(result["execution_id"] == EXPECTED_EXECUTION_ID, "result execution id mismatch")
    require(result["authorization_id"] == EXPECTED_AUTHORIZATION_ID, "result authorization mismatch")
    require(result["package_id"] == EXPECTED_PACKAGE_ID, "result package id mismatch")
    require(result["source_classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1", "classifier version changed")
    require(result["source_action_mapping_version"] == "METALS-V3-ACTION-MAPPING-1", "action mapping changed")
    require(result["validation_interval"] == {"start": "2023-08-22", "end": "2026-08-24"}, "validation interval changed")
    require(result["primary_horizon_trading_days"] == 63, "primary horizon changed")
    require(result["secondary_horizons_trading_days"] == [21, 126], "secondary horizons changed")
    require(result["minimum_compared_group_support"] == 20, "support floor changed")
    require(result["minimum_distinct_exposure_families_per_directional_state"] == 2, "family floor changed")
    require(result["label_ledger_sha256"] == manifest["label_ledger_sha256"], "result label hash mismatch")
    require(result["outcome_ledger_sha256"] == manifest["outcome_ledger_sha256"], "result outcome hash mismatch")
    require(result["label_ledger_hashed_before_outcome_calculation"] is True, "label-before-outcome boundary missing")
    require(result["v2_history_used_only_for_point_in_time_warmup"] is True, "V2 warmup boundary missing")
    require(result["v2_rows_entered_new_validation_labels_or_outcomes"] is False, "consumed V2 rows entered validation")
    require(result["secondary_horizons_cannot_substitute_for_primary_failure"] is True, "secondary rescue boundary changed")
    require(result["overlapping_forward_windows_present"] is True, "overlap disclosure missing")
    require(result["validation_result"] in {"PASS", "FAIL", "INCONCLUSIVE"}, "unexpected validation result")
    require(result["tactical_posture_authorized"] is False, "result unexpectedly authorizes tactical posture")

    require(len(labels) > 0, "label ledger is empty")
    for row in labels:
        require(row["observation_date"] >= "2023-08-22", "consumed date entered label ledger")
        require(row["observation_date"] <= "2026-08-24", "post-boundary date entered label ledger")
        require(row["candidate_regime"] in ACTION_MAP, "unexpected candidate regime")
        require(row["candidate_action_state"] == ACTION_MAP[row["candidate_regime"]], "action mapping mismatch")

    require(len(outcomes) > 0, "outcome ledger is empty")
    for row in outcomes:
        require(row["observation_date"] >= "2023-08-22", "consumed date entered outcome ledger")
        require(int(row["horizon_trading_days"]) in {21, 63, 126}, "unexpected outcome horizon")
        require(row["candidate_action_state"] in set(ACTION_MAP.values()), "unexpected outcome action state")

    primary = result["outcomes_by_action_state"]["63d"]
    supportive = primary["TACTICAL_SUPPORTIVE"]
    defensive = primary["TACTICAL_DEFENSIVE"]
    support_gate = supportive["observation_count"] >= 20 and defensive["observation_count"] >= 20
    family_gate = supportive["exposure_family_count"] >= 2 and defensive["exposure_family_count"] >= 2
    require(result["primary_support_gate_met"] is support_gate, "primary support gate mismatch")
    require(result["primary_exposure_family_gate_met"] is family_gate, "primary family gate mismatch")

    checks = result["primary_directional_checks"]
    if support_gate and family_gate:
        expected_checks = {
            "supportive_median_return_exceeds_defensive": supportive["median_forward_return_pct"] > defensive["median_forward_return_pct"],
            "supportive_positive_return_rate_exceeds_defensive": supportive["positive_return_rate"] > defensive["positive_return_rate"],
            "supportive_mean_mae_less_negative_than_defensive": supportive["mean_mae_pct"] > defensive["mean_mae_pct"],
        }
        require(checks == expected_checks, "primary directional checks mismatch")
        expected_result = "PASS" if all(expected_checks.values()) else "FAIL"
    else:
        expected_result = "INCONCLUSIVE"
    require(result["validation_result"] == expected_result, "governed validation result mismatch")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "execution_id": result["execution_id"],
        "validation_result": result["validation_result"],
        "label_ledger_sha256": manifest["label_ledger_sha256"],
        "outcome_ledger_sha256": manifest["outcome_ledger_sha256"],
        "validation_result_sha256": manifest["validation_result_sha256"],
        "primary_support_gate_met": result["primary_support_gate_met"],
        "primary_exposure_family_gate_met": result["primary_exposure_family_gate_met"],
        "all_three_primary_directional_checks_met": result["all_three_primary_directional_checks_met"],
        "supportive_63d_observation_count": supportive["observation_count"],
        "defensive_63d_observation_count": defensive["observation_count"],
        "supportive_63d_exposure_family_count": supportive["exposure_family_count"],
        "defensive_63d_exposure_family_count": defensive["exposure_family_count"],
        "tactical_posture_authorized": False,
        "next_decision": result["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
