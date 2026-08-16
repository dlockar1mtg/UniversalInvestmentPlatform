"""Fail-closed validation for the UIP R3 governance contract before domain review execution."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config" / "orchestration" / "r3_domain_review_contract.json"
STANDARD = ROOT / "docs" / "project_control" / "R3_GOVERNANCE_AND_DOMAIN_REVIEW_STANDARD.md"
R2_CERT = ROOT / "docs" / "project_control" / "generated" / "r2_refreshed_data_rehearsal" / "r2_refresh_rehearsal_certification.json"

AUTHORIZED_FINDINGS = {
    "PASS",
    "PASS_WITH_GOVERNED_GAPS",
    "REVIEW",
    "DOMAIN_INVESTIGATION_REQUIRED",
}
REQUIRED_DIMENSIONS = {
    "freshness_and_completeness",
    "native_self_consistency",
    "distribution_and_outliers",
    "change_from_prior_plausibility",
    "uip_semantic_preservation",
    "decision_readiness",
    "investigation_routing",
}
REQUIRED_DOMAINS = {"mtg", "metals", "crypto"}


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    require(STANDARD.is_file(), "R3 governing standard is missing")
    contract = load_json(CONTRACT)
    r2 = load_json(R2_CERT)

    require(
        contract.get("milestone") == "UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW",
        "Unexpected R3 milestone",
    )
    require(
        contract.get("governing_standard")
        == "docs/project_control/R3_GOVERNANCE_AND_DOMAIN_REVIEW_STANDARD.md",
        "R3 contract does not point to the governing standard",
    )
    require(
        set(contract.get("authorized_findings", [])) == AUTHORIZED_FINDINGS,
        "Authorized R3 findings do not match governance",
    )
    require(
        set(contract.get("required_dimensions", [])) == REQUIRED_DIMENSIONS,
        "R3 dimensions do not match governance",
    )

    rules = contract.get("global_rules", {})
    require(rules.get("native_authority_first") is True, "Native-authority-first rule missing")
    require(rules.get("missing_authority_may_be_synthesized") is False, "Missing authority synthesis unexpectedly allowed")
    require(rules.get("native_thresholds_may_be_invented_by_uip") is False, "UIP-native threshold invention unexpectedly allowed")
    require(rules.get("plausibility_equals_predictive_accuracy") is False, "Plausibility incorrectly equated with predictive accuracy")
    require(rules.get("cross_asset_ranking_authorized") is False, "Cross-asset ranking unexpectedly authorized")
    require(rules.get("cross_domain_allocation_authorized") is False, "Cross-domain allocation unexpectedly authorized")
    require(rules.get("automatic_execution_authorized") is False, "Automatic execution unexpectedly authorized")
    require(rules.get("suspicious_native_outputs_may_be_silently_corrected_by_uip") is False, "Silent UIP correction unexpectedly allowed")
    require(rules.get("failed_or_unresolved_material_evidence_may_enter_later_decision_logic") is False, "Unresolved material evidence unexpectedly allowed downstream")

    domains = contract.get("domains", {})
    require(set(domains) == REQUIRED_DOMAINS, "R3 contract must govern exactly MTG, Metals, and Crypto for this milestone")

    r2_domains = r2.get("domains", {})
    require(set(r2_domains) == REQUIRED_DOMAINS, "R2 certification does not contain exactly the three certified R3 domains")
    require(r2.get("status") == "UIP_R2_REFRESHED_DATA_REHEARSAL_PASS", "R2 certification is not PASS")

    review_orders = []
    for domain_id in sorted(REQUIRED_DOMAINS):
        domain = domains[domain_id]
        evidence_path = ROOT / domain["r2_evidence"]
        evidence = load_json(evidence_path)
        require(evidence.get("source_domain") == domain_id, f"{domain_id}: R2 evidence source_domain mismatch")
        require(r2_domains[domain_id].get("native_status") == "PASS", f"{domain_id}: R2 native status is not PASS")
        require(r2_domains[domain_id].get("freshness_status") == "PASS", f"{domain_id}: R2 freshness status is not PASS")
        require(r2_domains[domain_id].get("lineage_status") == "PASS", f"{domain_id}: R2 lineage status is not PASS")
        require(isinstance(domain.get("native_rules"), list) and domain["native_rules"], f"{domain_id}: native rules missing")
        require(isinstance(domain.get("prohibited_inferences"), list) and domain["prohibited_inferences"], f"{domain_id}: prohibited inferences missing")
        review_orders.append(int(domain.get("review_order", 0)))

    require(sorted(review_orders) == [1, 2, 3], "R3 review order must be unique and complete")

    policy = contract.get("finding_policy", {})
    require(set(policy) == AUTHORIZED_FINDINGS, "Finding policy must cover exactly the four governed findings")
    require(policy["PASS"].get("decision_ready") is True, "PASS must be decision-ready")
    require(policy["PASS_WITH_GOVERNED_GAPS"].get("decision_ready") is True, "PASS_WITH_GOVERNED_GAPS must be bounded decision-ready")
    require(policy["REVIEW"].get("decision_ready") is False, "REVIEW must block decision readiness")
    require(policy["DOMAIN_INVESTIGATION_REQUIRED"].get("decision_ready") is False, "DOMAIN_INVESTIGATION_REQUIRED must block decision readiness")

    closeout = contract.get("r3_closeout_requirements", {})
    require(closeout.get("cross_asset_ranking_created") is False, "R3 closeout unexpectedly permits cross-asset ranking")
    require(closeout.get("allocation_policy_created") is False, "R3 closeout unexpectedly permits allocation policy")
    require(closeout.get("automatic_execution_created") is False, "R3 closeout unexpectedly permits automatic execution")

    output = {
        "status": "UIP_R3_REVIEW_CONTRACT_VALIDATION_PASS",
        "governing_standard_present": True,
        "r2_certification_status": r2.get("status"),
        "domains": sorted(REQUIRED_DOMAINS),
        "dimensions": sorted(REQUIRED_DIMENSIONS),
        "authorized_findings": sorted(AUTHORIZED_FINDINGS),
        "native_authority_first": True,
        "missing_authority_synthesis": False,
        "predictive_accuracy_claim_created": False,
        "cross_asset_ranking_created": False,
        "allocation_policy_created": False,
        "automatic_execution_created": False,
        "next_gate": "IMPLEMENT_READ_ONLY_R3_DOMAIN_REVIEW_HARNESS",
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    print("UIP_R3_REVIEW_CONTRACT_VALIDATION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
