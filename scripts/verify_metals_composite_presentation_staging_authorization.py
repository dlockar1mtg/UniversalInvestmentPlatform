from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "config" / "metals" / "composite_presentation_staging_authorization.json"
EXPECTED_DB_SHA = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
EXPECTED_CANDIDATE = "metals-mtg-composite-recovery-r1-20260828"
EXPECTED_FINGERPRINT = "67352221b51e7479fe9e154e12dd718a9cf392c794d2320461203fe980bfc009"
EXPECTED_EVIDENCE = {
    "records_sha256": "e3058e6fd2c0315184cc63c4c0930c4152a6693deaa770a2534691330c11dbaa",
    "publication_sha256": "01e79b0f6e7d9791e18541ef308aa808f9b30a8cd14b97156deb91cb234d36ee",
    "proof_sha256": "679ea3097dd614cbf277bf3650bb464aca39176b7132ade723ec4d8af5638448",
    "manifest_sha256": "4a19c5c473ba594396500a1c36e1e08fca09330792f6c760c5e7f3761120dfa3",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    doc = json.loads(AUTH.read_text(encoding="utf-8"))
    candidate = doc["candidate"]
    cert = doc["candidate_certification"]
    contract = doc["staging_contract"]
    scope = doc["authorization_scope"]

    evidence_root = Path(candidate["evidence_root"])
    file_map = {
        "records_sha256": evidence_root / "composite_candidate_records.jsonl",
        "publication_sha256": evidence_root / "composite_candidate_publication.json",
        "proof_sha256": evidence_root / "composite_candidate_proof.json",
        "manifest_sha256": evidence_root / "composite_candidate_manifest.json",
    }
    evidence_present = evidence_root.is_dir() and all(path.is_file() for path in file_map.values())
    evidence_hashes_match = evidence_present and all(
        sha256_file(path) == EXPECTED_EVIDENCE[key] == candidate[key]
        for key, path in file_map.items()
    )

    results = {
        "authorization_id_bound": doc.get("authorization_id") == "METALS-COMPOSITE-PRESENTATION-STAGING-AUTHORIZATION-1",
        "source_head_bound": doc.get("source_governed_head") == "f133181af9cf53e96c5fa2bf769eaa27824bd3d5",
        "source_database_bound": doc.get("source_database_sha256") == EXPECTED_DB_SHA,
        "source_publications_bound": doc.get("source_active_publication_id") == "mtg-premium-stage-rehearsal-ac8adb415f03" and int(doc.get("source_active_record_count", -1)) == 13264 and doc.get("source_certified_metals_publication_id") == "metals-final-decision-presentation-r1-20260827",
        "candidate_identity_bound": candidate.get("publication_id") == EXPECTED_CANDIDATE and int(candidate.get("record_count", -1)) == 13264 and candidate.get("content_fingerprint") == EXPECTED_FINGERPRINT,
        "candidate_evidence_present": evidence_present,
        "candidate_evidence_hashes_match": evidence_hashes_match,
        "candidate_certification_bound": int(cert.get("active_records_preserved", -1)) == 13252 and int(cert.get("metals_recommendations_replaced", -1)) == 12 and int(cert.get("metals_final_action_match_count", -1)) == 12 and int(cert.get("mtg_premium_record_count", -1)) == 787 and int(cert.get("other_active_records_changed", -1)) == 0 and int(cert.get("certified_records_missing", -1)) == 0 and cert.get("local_candidate_certification_passed") is True,
        "staging_contract_bound": contract.get("stage_as_new_publication_only") is True and contract.get("required_publication_id") == EXPECTED_CANDIDATE and int(contract.get("required_record_count", -1)) == 13264 and contract.get("required_content_fingerprint") == EXPECTED_FINGERPRINT and all(contract.get(key) is True for key in ["validate_staged_record_count", "validate_three_domain_health_records", "validate_nonempty_asset_surface_for_crypto_metals_mtg", "validate_metals_final_actions_12_of_12", "validate_mtg_premium_records_787_of_787", "active_pointer_must_remain_source_active_after_staging"]),
        "staging_authorized": scope.get("read_hosted_presentation_records_authorized") is True and scope.get("hosted_publication_stage_authorized") is True and scope.get("hosted_staged_publication_validation_authorized") is True,
        "activation_closed": scope.get("hosted_publication_activation_authorized") is False and scope.get("active_pointer_mutation_authorized") is False,
        "other_writes_closed": all(scope.get(key) is False for key in ["repository_code_change_authorized", "analytical_database_write_authorized", "model_refresh_authorized", "forecast_refresh_authorized", "recommendation_recompute_authorized", "mtg_premium_recompute_authorized", "manual_render_deployment_authorized", "allocation_or_execution_authorized"]),
        "decision_bound": doc.get("authorization_decision") == "AUTHORIZE_BOUNDED_COMPOSITE_PRESENTATION_STAGING",
        "next_decision_bound": doc.get("next_decision") == "STAGE_AND_CERTIFY_BOUNDED_COMPOSITE_PRESENTATION_RECOVERY_CANDIDATE",
    }
    results["status"] = "PASS" if all(results.values()) else "FAIL"
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if results["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
