from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_REVIEW_ID = "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-REVIEW-1"
EXPECTED_EXECUTION_ID = "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-EXECUTION-1"
EXPECTED_LEDGER_SHA = "41f00a74c8116c59b5e36dc039db43a2481ffce9f1ce663da00c270d8c483dfd"
ALLOWED_STATUS = {
    "SUFFICIENT_FOR_REGIME_DEFINITION_LOCK_CONSIDERATION",
    "REQUIRES_FURTHER_RESEARCH_BEFORE_REGIME_DEFINITION_LOCK",
}
ALLOWED_NEXT = {
    "CONSIDER_LOCKING_METALS_TACTICAL_POLICY_V3_REGIME_DEFINITION",
    "DESIGN_NEXT_METALS_TACTICAL_POLICY_V3_REGIME_RESEARCH_ITERATION",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-path", required=True)
    args = parser.parse_args()

    path = Path(args.review_path).resolve()
    if not path.is_file():
        raise RuntimeError(f"review artifact missing: {path}")
    review = json.loads(path.read_text(encoding="utf-8"))

    if review.get("review_id") != EXPECTED_REVIEW_ID:
        raise RuntimeError("unexpected review id")
    if review.get("source_execution_id") != EXPECTED_EXECUTION_ID:
        raise RuntimeError("unexpected source execution id")
    if review.get("source_label_ledger_sha256") != EXPECTED_LEDGER_SHA:
        raise RuntimeError("unexpected source label ledger SHA-256")
    if review.get("research_role") != "DEVELOPMENT_ONLY_ON_CONSUMED_EVIDENCE":
        raise RuntimeError("research role changed")
    if review.get("overlapping_forward_windows_present") is not True:
        raise RuntimeError("overlapping-window disclosure missing")
    if review.get("observation_counts_are_not_independent_sample_counts") is not True:
        raise RuntimeError("independence limitation missing")
    if review.get("duplicate_exposure_families_are_not_independent_confirmation") is not True:
        raise RuntimeError("duplicate exposure-family limitation missing")
    if review.get("development_evidence_not_unseen_validation") is not True:
        raise RuntimeError("development-only disclosure missing")
    if review.get("v1_v2_intervals_remain_consumed") is not True:
        raise RuntimeError("consumed interval protection changed")
    if review.get("regime_definition_authorized") is not False:
        raise RuntimeError("regime definition unexpectedly authorized")
    if review.get("tactical_posture_authorized") is not False:
        raise RuntimeError("tactical posture unexpectedly authorized")
    if review.get("review_status") not in ALLOWED_STATUS:
        raise RuntimeError("unexpected review status")
    if review.get("next_decision") not in ALLOWED_NEXT:
        raise RuntimeError("unexpected next decision")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "review_id": review["review_id"],
        "source_execution_id": review["source_execution_id"],
        "source_label_ledger_sha256": review["source_label_ledger_sha256"],
        "eligible_opportunity_rows": int(review.get("eligible_opportunity_rows", 0)),
        "trend_persistence_count": int((review.get("regime_counts") or {}).get("TREND_PERSISTENCE", 0)),
        "mean_reversion_or_exhaustion_count": int((review.get("regime_counts") or {}).get("MEAN_REVERSION_OR_EXHAUSTION", 0)),
        "neutral_or_uncertain_count": int((review.get("regime_counts") or {}).get("NEUTRAL_OR_UNCERTAIN", 0)),
        "neutral_or_uncertain_rate": review.get("neutral_or_uncertain_rate"),
        "directional_support_gate_met": bool(review.get("directional_support_gate_met")),
        "directional_exposure_family_gate_met": bool(review.get("directional_exposure_family_gate_met")),
        "directional_return_separation_consistent_across_all_horizons": bool(review.get("directional_return_separation_consistent_across_all_horizons")),
        "review_status": review["review_status"],
        "regime_definition_authorized": False,
        "tactical_posture_authorized": False,
        "next_decision": review["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
