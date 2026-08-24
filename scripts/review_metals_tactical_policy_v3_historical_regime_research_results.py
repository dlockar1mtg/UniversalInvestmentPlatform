from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

EXPECTED_EXECUTION_ID = "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-EXECUTION-1"
EXPECTED_FREEZE_ID = "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-FREEZE-1"
EXPECTED_RULE_VERSION = "METALS-V3-REGIME-CANDIDATE-RULES-1"
EXPECTED_LEDGER_SHA = "41f00a74c8116c59b5e36dc039db43a2481ffce9f1ce663da00c270d8c483dfd"
DIRECTIONAL = ("TREND_PERSISTENCE", "MEAN_REVERSION_OR_EXHAUSTION")
NEUTRAL = "NEUTRAL_OR_UNCERTAIN"
HORIZONS = (21, 63, 126)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def as_int(value: str | int | float | None) -> int:
    return int(float(value)) if value is not None else 0


def as_float(value: str | int | float | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--review-output", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    review_output = Path(args.review_output).resolve()
    if review_output.exists():
        raise RuntimeError(f"review output already exists: {review_output}")

    required = {
        "manifest": output_dir / "manifest.json",
        "separability": output_dir / "regime_separability_summary.json",
        "conflict": output_dir / "conflict_and_neutral_assignment_summary.json",
        "support": output_dir / "regime_support_by_vehicle_and_exposure_family.csv",
        "outcomes": output_dir / "subsequent_outcome_research_summary.csv",
        "overlap": output_dir / "overlapping_forward_window_disclosure.json",
        "consumed": output_dir / "consumed_evidence_disclosure.json",
        "development": output_dir / "development_not_validation_disclosure.json",
    }
    for name, path in required.items():
        if not path.is_file():
            raise RuntimeError(f"missing persisted research artifact {name}: {path}")

    manifest = load_json(required["manifest"])
    separability = load_json(required["separability"])
    conflict = load_json(required["conflict"])
    overlap = load_json(required["overlap"])
    consumed = load_json(required["consumed"])
    development = load_json(required["development"])
    support_rows = load_csv(required["support"])
    outcome_rows = load_csv(required["outcomes"])

    if manifest.get("execution_id") != EXPECTED_EXECUTION_ID:
        raise RuntimeError("unexpected execution id")
    if manifest.get("freeze_id") != EXPECTED_FREEZE_ID:
        raise RuntimeError("unexpected freeze id")
    if manifest.get("rule_version") != EXPECTED_RULE_VERSION:
        raise RuntimeError("unexpected frozen rule version")
    if manifest.get("label_ledger_sha256") != EXPECTED_LEDGER_SHA:
        raise RuntimeError("unexpected label ledger SHA-256")
    if manifest.get("research_role") != "DEVELOPMENT_ONLY_ON_CONSUMED_EVIDENCE":
        raise RuntimeError("research role changed")
    if manifest.get("regime_definition_authorized") is not False:
        raise RuntimeError("regime definition unexpectedly authorized")
    if manifest.get("tactical_posture_authorized") is not False:
        raise RuntimeError("tactical posture unexpectedly authorized")
    if overlap.get("overlapping_forward_windows_present") is not True:
        raise RuntimeError("overlapping-window disclosure missing")
    if consumed.get("v1_v2_intervals_remain_consumed") is not True:
        raise RuntimeError("consumed interval protection changed")
    if development.get("development_evidence_not_unseen_validation") is not True:
        raise RuntimeError("development-only disclosure changed")

    regime_counts = {str(k): int(v) for k, v in (separability.get("candidate_regime_observation_counts") or {}).items()}
    family_counts = {str(k): int(v) for k, v in (separability.get("candidate_regime_exposure_family_counts") or {}).items()}
    minimum_support = int(separability.get("minimum_compared_group_support", 20))

    eligible = int(conflict.get("eligible_opportunity_rows", 0))
    neutral_rows = int(conflict.get("neutral_or_uncertain_rows", 0))
    neutral_rate = conflict.get("neutral_or_uncertain_rate")

    support_by_regime: dict[str, dict[str, Any]] = {}
    for regime in (*DIRECTIONAL, NEUTRAL):
        rows = [r for r in support_rows if r.get("candidate_regime") == regime and r.get("eligible", "").lower() == "true" and r.get("is_reference_control", "").lower() == "false"]
        support_by_regime[regime] = {
            "observation_count": sum(as_int(r.get("observation_count")) for r in rows),
            "vehicle_count": len({r.get("vehicle_id") for r in rows}),
            "exposure_family_count": len({r.get("exposure_family") for r in rows}),
            "exposure_families": sorted({str(r.get("exposure_family")) for r in rows if r.get("exposure_family")}),
        }

    outcome_by_regime: dict[str, dict[str, Any]] = {regime: {} for regime in (*DIRECTIONAL, NEUTRAL)}
    for row in outcome_rows:
        regime = str(row.get("candidate_regime"))
        if regime not in outcome_by_regime:
            continue
        horizon = as_int(row.get("horizon_trading_days"))
        if horizon not in HORIZONS:
            continue
        outcome_by_regime[regime][f"{horizon}d"] = {
            "observation_count": as_int(row.get("observation_count")),
            "vehicle_count": as_int(row.get("vehicle_count")),
            "exposure_family_count": as_int(row.get("exposure_family_count")),
            "mean_forward_return_pct": as_float(row.get("mean_forward_return_pct")),
            "median_forward_return_pct": as_float(row.get("median_forward_return_pct")),
            "positive_return_rate": as_float(row.get("positive_return_rate")),
            "mean_mae_pct": as_float(row.get("mean_mae_pct")),
            "mean_mfe_pct": as_float(row.get("mean_mfe_pct")),
        }

    directional_support_gate = all(regime_counts.get(regime, 0) >= minimum_support for regime in DIRECTIONAL)
    directional_family_gate = all(family_counts.get(regime, 0) >= 2 for regime in DIRECTIONAL)

    comparisons: dict[str, Any] = {}
    for horizon in HORIZONS:
        key = f"{horizon}d"
        trend = outcome_by_regime["TREND_PERSISTENCE"].get(key)
        exhaustion = outcome_by_regime["MEAN_REVERSION_OR_EXHAUSTION"].get(key)
        if not trend or not exhaustion:
            comparisons[key] = {"complete": False}
            continue
        comparisons[key] = {
            "complete": True,
            "trend_minus_exhaustion_mean_return_pct": trend["mean_forward_return_pct"] - exhaustion["mean_forward_return_pct"],
            "trend_minus_exhaustion_median_return_pct": trend["median_forward_return_pct"] - exhaustion["median_forward_return_pct"],
            "trend_minus_exhaustion_positive_return_rate": trend["positive_return_rate"] - exhaustion["positive_return_rate"],
            "trend_minus_exhaustion_mean_mae_pct": trend["mean_mae_pct"] - exhaustion["mean_mae_pct"],
            "trend_minus_exhaustion_mean_mfe_pct": trend["mean_mfe_pct"] - exhaustion["mean_mfe_pct"],
        }

    complete_comparisons = [value for value in comparisons.values() if value.get("complete")]
    return_direction_consistency = (
        len(complete_comparisons) == len(HORIZONS)
        and all(value["trend_minus_exhaustion_median_return_pct"] > 0 for value in complete_comparisons)
        and all(value["trend_minus_exhaustion_positive_return_rate"] > 0 for value in complete_comparisons)
    )

    review_status = "SUFFICIENT_FOR_REGIME_DEFINITION_LOCK_CONSIDERATION" if (
        directional_support_gate and directional_family_gate and return_direction_consistency
    ) else "REQUIRES_FURTHER_RESEARCH_BEFORE_REGIME_DEFINITION_LOCK"

    review = {
        "review_id": "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-REVIEW-1",
        "source_execution_id": EXPECTED_EXECUTION_ID,
        "source_freeze_id": EXPECTED_FREEZE_ID,
        "source_rule_version": EXPECTED_RULE_VERSION,
        "source_label_ledger_sha256": EXPECTED_LEDGER_SHA,
        "research_role": "DEVELOPMENT_ONLY_ON_CONSUMED_EVIDENCE",
        "eligible_opportunity_rows": eligible,
        "regime_counts": regime_counts,
        "regime_exposure_family_counts": family_counts,
        "neutral_or_uncertain_rows": neutral_rows,
        "neutral_or_uncertain_rate": neutral_rate,
        "support_by_regime": support_by_regime,
        "outcomes_by_regime": outcome_by_regime,
        "directional_comparisons": comparisons,
        "directional_support_gate_met": directional_support_gate,
        "directional_exposure_family_gate_met": directional_family_gate,
        "directional_return_separation_consistent_across_all_horizons": return_direction_consistency,
        "overlapping_forward_windows_present": True,
        "observation_counts_are_not_independent_sample_counts": True,
        "duplicate_exposure_families_are_not_independent_confirmation": True,
        "development_evidence_not_unseen_validation": True,
        "v1_v2_intervals_remain_consumed": True,
        "regime_definition_authorized": False,
        "tactical_posture_authorized": False,
        "review_status": review_status,
        "next_decision": "CONSIDER_LOCKING_METALS_TACTICAL_POLICY_V3_REGIME_DEFINITION" if review_status == "SUFFICIENT_FOR_REGIME_DEFINITION_LOCK_CONSIDERATION" else "DESIGN_NEXT_METALS_TACTICAL_POLICY_V3_REGIME_RESEARCH_ITERATION",
    }

    review_output.parent.mkdir(parents=True, exist_ok=True)
    review_output.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(review, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
