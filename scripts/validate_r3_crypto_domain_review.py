from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs" / "project_control" / "generated" / "r3_output_rationality_review" / "crypto_r3_domain_review.json"
CONTRACT = ROOT / "config" / "orchestration" / "r3_domain_review_contract.json"

EXPECTED_DIMENSIONS = {
    "freshness_and_completeness",
    "native_self_consistency",
    "distribution_and_outliers",
    "change_from_prior_plausibility",
    "uip_semantic_preservation",
    "decision_readiness",
    "investigation_routing",
}
ALLOWED_DIMENSION_STATUSES = {"PASS", "PASS_WITH_GOVERNED_GAP"}
ALLOWED_MAPPINGS = {
    "BUY": "buy",
    "ACCUMULATE": "accumulate",
    "HOLD": "hold",
    "WAIT": "watch",
    "REDUCE": "reduce",
    "SELL": "sell",
    "AVOID": "sell",
}


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(f"Missing required evidence: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    review = load_json(REVIEW)
    contract = load_json(CONTRACT)

    if review.get("domain_id") != "crypto":
        raise RuntimeError("Crypto R3 review domain_id is incorrect.")
    if review.get("milestone") != "UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW":
        raise RuntimeError("Crypto R3 review milestone is incorrect.")
    if review.get("finding") != "PASS_WITH_GOVERNED_GAPS":
        raise RuntimeError(f"Unexpected Crypto R3 finding: {review.get('finding')!r}")
    if review.get("review_authority_mode") != "R3_PERSISTED_RECAPTURE":
        raise RuntimeError("Crypto R3 review authority mode is incorrect.")

    dimensions = review.get("dimension_results", {})
    if set(dimensions) != EXPECTED_DIMENSIONS:
        raise RuntimeError("Crypto R3 review does not contain exactly the seven governed dimensions.")
    invalid_statuses = {
        name: payload.get("status")
        for name, payload in dimensions.items()
        if payload.get("status") not in ALLOWED_DIMENSION_STATUSES
    }
    if invalid_statuses:
        raise RuntimeError(f"Crypto R3 dimension status failure: {invalid_statuses}")

    if dimensions["change_from_prior_plausibility"].get("status") != "PASS_WITH_GOVERNED_GAP":
        raise RuntimeError("Crypto exact-prior comparison gap is not preserved in change-from-prior dimension.")
    if dimensions["decision_readiness"].get("status") != "PASS_WITH_GOVERNED_GAP":
        raise RuntimeError("Crypto bounded decision-readiness gap is not preserved.")

    gaps = review.get("governed_gaps", [])
    if len(gaps) != 1 or "Exact row-level R2 Crypto package was not retained" not in str(gaps[0]):
        raise RuntimeError("Crypto exact-R2 row evidence gap is missing or altered.")

    native = dimensions["native_self_consistency"].get("evidence", {})
    mapping = native.get("native_to_universal_mapping", [])
    if not mapping:
        raise RuntimeError("Crypto native recommendation mapping evidence is empty.")
    for item in mapping:
        source = str(item.get("native", "")).upper()
        target = str(item.get("universal", "")).lower()
        if source not in ALLOWED_MAPPINGS:
            raise RuntimeError(f"Unknown Crypto native recommendation label in R3 evidence: {source!r}")
        if target != ALLOWED_MAPPINGS[source]:
            raise RuntimeError(f"Crypto recommendation mapping mismatch in R3 evidence: {source}->{target}")

    semantic = dimensions["uip_semantic_preservation"].get("evidence", {})
    if semantic.get("absent_holdings_preserved") is not True:
        raise RuntimeError("Crypto absent-holdings semantic was not preserved.")
    if semantic.get("source_database_unchanged") is not True:
        raise RuntimeError("Crypto source database unchanged evidence is not true.")
    if semantic.get("is_exact_r2_output") is not False:
        raise RuntimeError("Crypto persisted recapture is incorrectly represented as exact R2 output.")

    if review.get("observed_anomalies") != []:
        raise RuntimeError(f"Crypto R3 review contains unresolved anomalies: {review.get('observed_anomalies')}")
    if review.get("cross_asset_ranking_created") is not False:
        raise RuntimeError("Crypto R3 review created cross-asset ranking authority.")
    if review.get("allocation_policy_created") is not False:
        raise RuntimeError("Crypto R3 review created allocation authority.")
    if review.get("automatic_execution_created") is not False:
        raise RuntimeError("Crypto R3 review created execution authority.")
    if review.get("predictive_accuracy_certified") is not False:
        raise RuntimeError("Crypto R3 review improperly certified predictive accuracy.")

    crypto_contract = contract.get("domains", {}).get("crypto", {})
    if crypto_contract.get("review_authority_mode") != "R3_PERSISTED_RECAPTURE_REQUIRED":
        raise RuntimeError("R3 contract Crypto authority mode changed unexpectedly.")

    result = {
        "status": "UIP_R3_CRYPTO_DOMAIN_REVIEW_VALIDATION_PASS",
        "finding": review.get("finding"),
        "dimension_count": len(dimensions),
        "governed_gap_count": len(gaps),
        "observed_anomaly_count": len(review.get("observed_anomalies", [])),
        "recommendation_mapping_count": len(mapping),
        "decision_ready_bounded": True,
        "predictive_accuracy_certified": False,
        "cross_asset_ranking_created": False,
        "allocation_policy_created": False,
        "automatic_execution_created": False,
        "next_gate": "R3_METALS_OUTPUT_RATIONALITY_REVIEW_AFTER_CRYPTO_EVIDENCE_COMMIT",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    print("UIP_R3_CRYPTO_DOMAIN_REVIEW_VALIDATION=PASS")
    print("NEXT_GATE=R3_METALS_OUTPUT_RATIONALITY_REVIEW_AFTER_CRYPTO_EVIDENCE_COMMIT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
