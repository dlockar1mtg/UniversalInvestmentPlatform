from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R2_ROOT = ROOT / "docs" / "project_control" / "generated" / "r2_refreshed_data_rehearsal"


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(f"Missing required evidence: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def existing_path(value: str | None) -> bool:
    if not value:
        return False
    try:
        return Path(value).exists()
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit whether the exact R2-certified domain outputs needed for R3 are still retrievable without mutating source or UIP state."
    )
    parser.add_argument(
        "--r2-worktree",
        type=Path,
        default=None,
        help="Optional local R2 worktree used to locate ignored/runtime Metals outputs that are not present in a fresh R3 worktree.",
    )
    args = parser.parse_args()

    certification = load_json(R2_ROOT / "r2_refresh_rehearsal_certification.json")
    if certification.get("status") != "UIP_R2_REFRESHED_DATA_REHEARSAL_PASS":
        raise RuntimeError("R2 consolidated certification is not PASS.")

    crypto = load_json(R2_ROOT / "crypto_r2_rehearsal_evidence.json")
    metals = load_json(R2_ROOT / "metals_r2_rehearsal_evidence.json")
    mtg = load_json(R2_ROOT / "mtg_r2_rehearsal_evidence.json")

    crypto_output_dir = str(crypto.get("universal_export", {}).get("output_directory", ""))
    crypto_exact_local = existing_path(crypto_output_dir)

    r2_worktree = args.r2_worktree.resolve() if args.r2_worktree else None
    metals_candidates: list[Path] = []
    if r2_worktree:
        metals_candidates.extend(
            [
                r2_worktree / "data" / "integration" / "metals" / "latest",
                r2_worktree / "data" / "operations" / "metals" / "daily_market_overlay",
                r2_worktree / "data" / "operations" / "metals" / "cycle_history",
            ]
        )
    metals_existing = [str(path) for path in metals_candidates if path.exists()]
    metals_exact_local = len(metals_existing) == len(metals_candidates) and bool(metals_candidates)

    mtg_run_id = str(mtg.get("source_workflow_run_id", ""))
    mtg_artifact_sha = str(mtg.get("source_artifact_sha256", ""))
    mtg_remote_retrieval_identity_present = bool(mtg_run_id and mtg_artifact_sha)

    availability = {
        "status": "UIP_R3_EXACT_OUTPUT_AVAILABILITY_AUDIT_COMPLETE",
        "r2_certification_status": certification.get("status"),
        "domains": {
            "crypto": {
                "exact_output_local_path": crypto_output_dir or None,
                "exact_output_local_available": crypto_exact_local,
                "package_id": crypto.get("package_id"),
                "fresh_run_id": crypto.get("fresh_run_id"),
                "disposition": (
                    "EXACT_R2_OUTPUT_LOCALLY_AVAILABLE"
                    if crypto_exact_local
                    else "EXACT_R2_OUTPUT_NOT_PERSISTED_LOCALLY_RECAPTURE_OR_DURABLE_ARTIFACT_REQUIRED"
                ),
            },
            "metals": {
                "package_id": metals.get("package_id"),
                "r2_runtime_candidates": [str(path) for path in metals_candidates],
                "existing_runtime_paths": metals_existing,
                "exact_runtime_evidence_locally_available": metals_exact_local,
                "disposition": (
                    "EXACT_R2_RUNTIME_EVIDENCE_LOCALLY_AVAILABLE"
                    if metals_exact_local
                    else "R2_RUNTIME_EVIDENCE_LOCATION_REQUIRES_RESOLUTION"
                ),
            },
            "mtg": {
                "source_workflow_run_id": mtg_run_id or None,
                "source_artifact_sha256": mtg_artifact_sha or None,
                "remote_retrieval_identity_present": mtg_remote_retrieval_identity_present,
                "disposition": (
                    "GITHUB_ARTIFACT_RETRIEVAL_PATH_IDENTIFIED"
                    if mtg_remote_retrieval_identity_present
                    else "MTG_EXACT_ARTIFACT_AUTHORITY_MISSING"
                ),
            },
        },
        "governance": {
            "r3_must_review_exact_r2_certified_outputs": True,
            "summary_only_evidence_is_sufficient_for_distribution_review": False,
            "missing_exact_output_may_be_synthesized": False,
            "fresh_rerun_may_be_silently_substituted_for_exact_r2_output": False,
        },
        "next_gate": "RESOLVE_EXACT_R2_OUTPUT_RETRIEVAL_BEFORE_DOMAIN_RATIONALITY_REVIEW",
    }

    print(json.dumps(availability, indent=2, sort_keys=True))
    print("UIP_R3_EXACT_OUTPUT_AVAILABILITY_AUDIT=COMPLETE")

    if not crypto_exact_local:
        print("CRYPTO_EXACT_R2_OUTPUT_AVAILABLE=FALSE")
    else:
        print("CRYPTO_EXACT_R2_OUTPUT_AVAILABLE=TRUE")
    print(f"METALS_EXACT_R2_RUNTIME_AVAILABLE={'TRUE' if metals_exact_local else 'FALSE'}")
    print(f"MTG_REMOTE_ARTIFACT_IDENTITY_AVAILABLE={'TRUE' if mtg_remote_retrieval_identity_present else 'FALSE'}")
    print("NEXT_GATE=RESOLVE_EXACT_R2_OUTPUT_RETRIEVAL_BEFORE_DOMAIN_RATIONALITY_REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
