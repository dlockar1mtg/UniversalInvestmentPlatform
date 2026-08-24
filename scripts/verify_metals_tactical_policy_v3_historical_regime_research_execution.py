from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REQUIRED_FILES = [
    "versioned_candidate_input_definition.json",
    "versioned_candidate_regime_assignment_logic.json",
    "point_in_time_regime_label_ledger.csv",
    "point_in_time_regime_label_ledger_sha256.txt",
    "regime_support_by_vehicle_and_exposure_family.csv",
    "regime_separability_summary.json",
    "conflict_and_neutral_assignment_summary.json",
    "subsequent_outcome_research_summary.csv",
    "overlapping_forward_window_disclosure.json",
    "consumed_evidence_disclosure.json",
    "development_not_validation_disclosure.json",
    "manifest.json",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    if not output_dir.is_dir():
        raise RuntimeError("historical regime research output directory is missing")

    for name in REQUIRED_FILES:
        if not (output_dir / name).is_file():
            raise RuntimeError(f"required execution output is missing: {name}")

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("execution_id") != "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-EXECUTION-1":
        raise RuntimeError("unexpected execution id")
    if manifest.get("freeze_id") != "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-FREEZE-1":
        raise RuntimeError("unexpected freeze id")
    if manifest.get("rule_version") != "METALS-V3-REGIME-CANDIDATE-RULES-1":
        raise RuntimeError("unexpected rule version")
    if manifest.get("research_role") != "DEVELOPMENT_ONLY_ON_CONSUMED_EVIDENCE":
        raise RuntimeError("research role changed")
    if int(manifest.get("history_row_count", -1)) != 10274:
        raise RuntimeError("unexpected history row count")
    if int(manifest.get("vehicle_count", -1)) != 11:
        raise RuntimeError("unexpected vehicle count")
    if int(manifest.get("observations_per_vehicle", -1)) != 934:
        raise RuntimeError("unexpected per-vehicle observation count")
    if int(manifest.get("label_ledger_row_count", -1)) != 10274:
        raise RuntimeError("unexpected label ledger row count")

    ledger = output_dir / "point_in_time_regime_label_ledger.csv"
    ledger_sha = sha256_file(ledger)
    recorded_sha = (output_dir / "point_in_time_regime_label_ledger_sha256.txt").read_text(encoding="ascii").strip()
    if ledger_sha != recorded_sha:
        raise RuntimeError("label ledger SHA-256 file does not match ledger")
    if manifest.get("label_ledger_sha256") != ledger_sha:
        raise RuntimeError("manifest label ledger SHA-256 does not match ledger")

    output_hashes = manifest.get("output_files") or {}
    for name, expected_sha in output_hashes.items():
        path = output_dir / name
        if not path.is_file():
            raise RuntimeError(f"manifest output is missing: {name}")
        if sha256_file(path) != expected_sha:
            raise RuntimeError(f"manifest hash mismatch: {name}")

    consumed = json.loads((output_dir / "consumed_evidence_disclosure.json").read_text(encoding="utf-8"))
    if consumed.get("research_role") != "DEVELOPMENT_ONLY_ON_CONSUMED_EVIDENCE":
        raise RuntimeError("consumed evidence disclosure changed research role")
    if consumed.get("v1_v2_intervals_remain_consumed") is not True:
        raise RuntimeError("consumed intervals were not preserved")
    if consumed.get("unseen_validation_claim_authorized") is not False:
        raise RuntimeError("unseen validation claim unexpectedly authorized")

    development = json.loads((output_dir / "development_not_validation_disclosure.json").read_text(encoding="utf-8"))
    for key in (
        "development_evidence_not_unseen_validation",
    ):
        if development.get(key) is not True:
            raise RuntimeError(f"required development disclosure missing: {key}")
    for key in (
        "v3_regime_definition_authorized",
        "tactical_posture_authorized",
        "new_validation_outcome_inspection_authorized",
        "presentation_activation_authorized",
        "production_database_write_authorized",
    ):
        if development.get(key) is not False:
            raise RuntimeError(f"prohibited authority changed: {key}")

    overlap = json.loads((output_dir / "overlapping_forward_window_disclosure.json").read_text(encoding="utf-8"))
    if overlap.get("overlapping_forward_windows_present") is not True:
        raise RuntimeError("overlapping forward-window disclosure missing")
    if overlap.get("independence_claim_prohibited") is not True:
        raise RuntimeError("independence-claim prohibition missing")
    if overlap.get("horizons_trading_days") != [21, 63, 126]:
        raise RuntimeError("unexpected forward horizons")

    if manifest.get("regime_definition_authorized") is not False:
        raise RuntimeError("regime definition unexpectedly authorized")
    if manifest.get("tactical_posture_authorized") is not False:
        raise RuntimeError("tactical posture unexpectedly authorized")
    if manifest.get("unseen_validation_claim_authorized") is not False:
        raise RuntimeError("unseen validation claim unexpectedly authorized")
    if manifest.get("next_decision") != "REVIEW_METALS_TACTICAL_POLICY_V3_HISTORICAL_REGIME_RESEARCH_RESULTS":
        raise RuntimeError("unexpected next decision")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "execution_id": manifest["execution_id"],
        "freeze_id": manifest["freeze_id"],
        "rule_version": manifest["rule_version"],
        "research_role": manifest["research_role"],
        "history_row_count": manifest["history_row_count"],
        "vehicle_count": manifest["vehicle_count"],
        "observations_per_vehicle": manifest["observations_per_vehicle"],
        "label_ledger_row_count": manifest["label_ledger_row_count"],
        "label_ledger_sha256": ledger_sha,
        "directional_regime_minimum_support_gate_met": manifest["directional_regime_minimum_support_gate_met"],
        "overlapping_forward_windows_disclosed": True,
        "consumed_intervals_remain_consumed": True,
        "development_not_validation": True,
        "regime_definition_authorized": False,
        "tactical_posture_authorized": False,
        "unseen_validation_claim_authorized": False,
        "next_decision": manifest["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
