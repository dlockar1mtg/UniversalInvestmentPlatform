from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STANDARD = ROOT / "docs" / "project_control" / "R3_GOVERNANCE_AND_DOMAIN_REVIEW_STANDARD.md"
LEDGER = ROOT / "docs" / "project_control" / "06_CHANGE_LEDGER.md"
CONTRACT = ROOT / "config" / "orchestration" / "r3_domain_review_contract.json"
EVIDENCE = ROOT / "docs" / "project_control" / "generated" / "r3_output_rationality_review" / "r3_exact_output_governance_correction.json"

STANDARD_MARKER = "## Exact-output evidence availability correction"
LEDGER_MARKER = "## UIP-CHG-2026-034 - Bound R3 Exact-Output Review to Available Certified Evidence"

STANDARD_APPEND = r'''

## Exact-output evidence availability correction

R3 remains anchored to the R2-certified cycle, but the exact row-level R2 output must not be fabricated when R2 execution did not durably persist that output.

The governed evidence modes are:

- MTG: review the exact R2 source artifact identified by workflow run `31843560745` and artifact digest `sha256:1885fd950f4b01d00d71719c5ba34261a5b9a442ec61b17e19587decd4b265bc`.
- Metals: review the exact locally retained R2 runtime package, cycle evidence, and daily-market overlay associated with package `metals-20260814T232106Z-f3577228`.
- Crypto: the exact row-level package from R2 run `crypto-prod-20260815T122413Z-e7429e07` was created inside disposable temporary storage and was not durably persisted. R3 may not reconstruct, synthesize, or label a later run as that exact R2 package.

For Crypto only, R3 is authorized to perform one controlled persisted recapture using the same certified source commit/version and the already-governed populated-database incremental refresh path on a disposable database copy. The recapture must:

- preserve the source production database unchanged;
- use the certified source commit/version recorded in R2;
- use the supported native incremental refresh path already governed in R2;
- persist the complete review package and file hashes before temporary state is removed;
- be labeled `R3_PERSISTED_RECAPTURE`, never `EXACT_R2_OUTPUT`;
- retain the R2 run/package summary as prior-cycle authority;
- treat unavailable exact row-to-row R2 comparison as a governed evidence gap rather than inventing a comparison.

This correction does not reopen, replace, or retroactively modify the R2 certification. It narrows how R3 obtains reviewable row-level evidence after the availability audit proved that the Crypto R2 row package was not retained.

A Crypto R3 finding cannot claim an exact row-to-row change-from-prior review against R2 unless the original R2 package is later recovered. That limitation must remain explicit in `governed_gaps` and may require `PASS_WITH_GOVERNED_GAPS` even if all currently reviewable evidence is otherwise decision-ready.
'''

LEDGER_APPEND = r'''

## UIP-CHG-2026-034 - Bound R3 Exact-Output Review to Available Certified Evidence

Date: 2026-08-15
Status: ACTIVE
Type: DATA_GOVERNANCE, CERTIFICATION, R3_EVIDENCE_POLICY
Approval authority: Devon Lockard

Decision:

Preserve the R3 requirement to review exact R2-certified row-level output wherever that output still exists, while prohibiting reconstruction or synthesis when it does not.

Evidence availability audit:

- MTG: exact R2 GitHub artifact retrieval identity is available for workflow run `31843560745`, digest `sha256:1885fd950f4b01d00d71719c5ba34261a5b9a442ec61b17e19587decd4b265bc`.
- Metals: exact R2 runtime package, cycle history, and daily-market overlay remain locally available.
- Crypto: exact R2 row-level package for `crypto-prod-20260815T122413Z-e7429e07` was not persisted because the disposable rehearsal removed its temporary directory after successful validation.

New governed rule:

- exact R2 output remains mandatory where available;
- missing exact R2 output may not be synthesized or silently replaced;
- for Crypto only, one controlled `R3_PERSISTED_RECAPTURE` is authorized using the same certified source commit/version and supported populated-database incremental refresh path on a disposable database copy;
- the recapture must be durably persisted with hashes before review;
- the recapture is not the exact R2 package and may not be labeled as such;
- unavailable exact row-to-row R2 comparison remains an explicit governed gap in R3.

Prior state:

`R3_REQUIRES_EXACT_R2_ROW_OUTPUT_FOR_ALL_DOMAIN_REVIEW_DIMENSIONS`

New state:

`R3_USES_EXACT_R2_OUTPUT_WHERE_AVAILABLE_AND_FAIL_CLOSED_PERSISTED_RECAPTURE_WHERE_NOT_RETAINED`

Architecture impact:

None. Native domain ownership, UIP integration boundaries, and production activation rules are unchanged.

Certification impact:

R2 remains certified and unchanged. R3 must disclose the Crypto exact-prior-row evidence gap and may not claim a comparison that cannot be proven.

Risk/cost impact:

No paid provider is introduced. Crypto recapture uses the already-certified no-paid-CoinGecko incremental path and disposable state.

Reversal:

`FULLY_REVERSIBLE`

Next required action:

`PERSIST_R3_CRYPTO_RECAPTURE_AND_RETRIEVE_EXACT_MTG_R2_ARTIFACT`

---
'''


def append_once(path: Path, marker: str, addition: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return False
    normalized_addition = addition.strip("\r\n")
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text.rstrip("\r\n") + "\n\n" + normalized_addition + "\n")
    return True


def main() -> int:
    for path in (STANDARD, LEDGER, CONTRACT):
        if not path.is_file():
            raise RuntimeError(f"Missing governance authority: {path}")

    standard_changed = append_once(STANDARD, STANDARD_MARKER, STANDARD_APPEND)
    ledger_changed = append_once(LEDGER, LEDGER_MARKER, LEDGER_APPEND)

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("milestone") != "UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW":
        raise RuntimeError("Unexpected R3 contract milestone.")
    if contract.get("global_rules", {}).get("missing_authority_may_be_synthesized") is not False:
        raise RuntimeError("R3 contract no longer fails closed on missing authority.")

    contract["exact_output_policy"] = {
        "exact_r2_output_required_where_available": True,
        "missing_exact_r2_output_may_be_synthesized": False,
        "r3_persisted_recapture_allowed_when_exact_r2_not_retained": True,
        "recapture_must_use_certified_source_commit_or_version": True,
        "recapture_must_use_supported_native_refresh_path": True,
        "recapture_must_use_disposable_source_state": True,
        "recapture_must_be_durably_persisted_with_hashes": True,
        "recapture_may_be_labeled_exact_r2_output": False,
        "unavailable_exact_prior_row_comparison_is_governed_gap": True,
    }
    contract["domains"]["crypto"]["review_authority_mode"] = "R3_PERSISTED_RECAPTURE_REQUIRED"
    contract["domains"]["crypto"]["exact_r2_output_persisted"] = False
    contract["domains"]["metals"]["review_authority_mode"] = "EXACT_R2_RUNTIME_EVIDENCE"
    contract["domains"]["mtg"]["review_authority_mode"] = "EXACT_R2_REMOTE_ARTIFACT"

    CONTRACT.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    payload = {
        "status": "UIP_R3_EXACT_OUTPUT_GOVERNANCE_CORRECTION_APPLIED",
        "change_id": "UIP-CHG-2026-034",
        "r2_certification_changed": False,
        "exact_r2_output_required_where_available": True,
        "missing_exact_r2_output_may_be_synthesized": False,
        "crypto_review_authority_mode": "R3_PERSISTED_RECAPTURE_REQUIRED",
        "crypto_recapture_may_be_labeled_exact_r2_output": False,
        "crypto_exact_prior_row_comparison_gap_preserved": True,
        "metals_review_authority_mode": "EXACT_R2_RUNTIME_EVIDENCE",
        "mtg_review_authority_mode": "EXACT_R2_REMOTE_ARTIFACT",
        "next_gate": "PERSIST_R3_CRYPTO_RECAPTURE_AND_RETRIEVE_EXACT_MTG_R2_ARTIFACT",
        "standard_updated": standard_changed,
        "ledger_updated": ledger_changed,
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    print("UIP_R3_EXACT_OUTPUT_GOVERNANCE_CORRECTION=PASS")
    print(f"EVIDENCE_OUTPUT={EVIDENCE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
