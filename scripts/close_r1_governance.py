from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START = ROOT / "docs" / "project_control" / "00_START_HERE.md"
ROADMAP = ROOT / "docs" / "project_control" / "04_ACTIVE_ROADMAP.md"
STATE = ROOT / "docs" / "project_control" / "05_PROJECT_STATE.md"
LEDGER = ROOT / "docs" / "project_control" / "06_CHANGE_LEDGER.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _replace_once(path: Path, old: str, new: str) -> None:
    text = _read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one anchor in {path}; found {count}: {old!r}"
        )
    _write(path, text.replace(old, new, 1))


def _append_once(path: Path, marker: str, section: str) -> None:
    text = _read(path)
    if marker in text:
        raise RuntimeError(f"Section already exists in {path}: {marker}")
    _write(path, text.rstrip() + "\n\n" + section.strip() + "\n")


def close_start_here() -> None:
    _replace_once(
        START,
        "`1babdacdc101e40f6f4550b56883ccc7b2d0f674`",
        "`55d5c72582bf70aff21a30b69edadab9ea9e8553`",
    )
    _replace_once(
        START,
        "Current next authorized action:\n\n`UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS`",
        "Current next authorized action:\n\n`UIP_R2_REFRESHED_DATA_REHEARSAL`",
    )
    _replace_once(
        START,
        "The controlled recovery evidence remains preserved. Under `UIP-CHG-2026-026` through `UIP-CHG-2026-031`, MTG, Metals, Crypto, and D1 are certified complete. The active next action is R1 governed refresh and orchestration contracts. Certified native-domain and D1 work must not be reopened without a verified governance defect.",
        "The controlled recovery evidence remains preserved. Under `UIP-CHG-2026-026` through `UIP-CHG-2026-032`, MTG, Metals, Crypto, D1, and R1 are certified complete. The active next action is R2 real refreshed-data rehearsal, followed by the governed R3 output-rationality/domain-health gate before E1 or dashboard decision logic. Certified native-domain, D1, and R1 work must not be reopened without a verified governance defect.",
    )


def close_roadmap() -> None:
    _replace_once(
        ROADMAP,
        "- `UIP_D1_COMMON_DOMAIN_REGISTRY_AND_LINEAGE_INTERFACE`\n",
        "- `UIP_D1_COMMON_DOMAIN_REGISTRY_AND_LINEAGE_INTERFACE`\n- `UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS`\n",
    )
    _replace_once(
        ROADMAP,
        "Current milestone:\n\n`UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS`\n\nNext authorized action:\n\n`IMPLEMENT_REFRESH_AND_ORCHESTRATION_CONTRACTS`\n\nExpected subsequent action:\n\n`UIP_R2_REFRESHED_DATA_REHEARSAL`",
        "Current milestone:\n\n`UIP_R2_REFRESHED_DATA_REHEARSAL`\n\nNext authorized action:\n\n`EXECUTE_REAL_REFRESHED_DATA_REHEARSAL`\n\nExpected subsequent action:\n\n`UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW`",
    )


def close_state() -> None:
    _replace_once(
        STATE,
        "Current milestone:\nUIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS",
        "Current milestone:\nUIP_R2_REFRESHED_DATA_REHEARSAL",
    )
    _replace_once(
        STATE,
        "Next authorized action:\nUIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS",
        "Next authorized action:\nUIP_R2_REFRESHED_DATA_REHEARSAL",
    )
    _replace_once(
        STATE,
        "`1babdacdc101e40f6f4550b56883ccc7b2d0f674`",
        "`55d5c72582bf70aff21a30b69edadab9ea9e8553`",
    )
    _replace_once(
        STATE,
        "`phase-uip-d1-common-domain-registry`",
        "`phase-uip-r1-refresh-orchestration`",
    )
    _replace_once(
        STATE,
        "6. `UIP-R1` - establish governed refresh and orchestration contracts.\n7. `UIP-R2` - perform refreshed-data rehearsals for MTG, Metals, and Crypto.\n8. `UIP-E1` - establish the future Stocks/ETF extension boundary.\n9. `UIP-DASH-1` and `UIP-DASH-2` - build the dashboard on certified multi-domain inputs.\n10. Govern future cross-asset ranking, comparison, or allocation methodology separately.",
        "6. `UIP-R1` - establish governed refresh and orchestration contracts.\n7. `UIP-R2` - perform real refreshed-data rehearsals for MTG, Metals, and Crypto.\n8. `UIP-R3` - certify output rationality, domain health, anomaly routing, and decision readiness without creating cross-asset ranking or allocation policy.\n9. `UIP-E1` - establish the future Stocks/ETF extension boundary.\n10. `UIP-DASH-1` and `UIP-DASH-2` - build the dashboard on certified multi-domain inputs.\n11. Govern future cross-asset ranking, comparison, or allocation methodology separately.",
    )
    section = """
## UIP-R1 certification closeout

R1 status:

`UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACT_CERTIFICATION_PASS`

Governed main base:

`55d5c72582bf70aff21a30b69edadab9ea9e8553`

Technical contract head before certification evidence:

`026169f85f411c4b76061a5c9e4b42de944efba4`

Certified authority and controls:

- machine-readable contract: `config/orchestration/r1_domain_refresh_contracts.json`;
- typed fail-closed interface: `foundation/orchestration/refresh_contracts.py`;
- human-readable contract: `docs/project_control/R1_REFRESH_ORCHESTRATION_CONTRACT.md`;
- certified domains: MTG, Metals, Crypto;
- required cycle evidence fields: 19;
- external domains use source-owned GitHub workflow dispatch;
- UIP direct invocation of external collectors remains prohibited;
- Metals remains UIP-native and uses its canonical production entrypoint;
- failed refresh cycles preserve the latest certified UIP state;
- partial activation is prohibited;
- missing authority may not be synthesized;
- current asset populations are not permanent constants;
- MTG refreshed-delivery compatibility remains an explicit R2 proof requirement;
- R1 focused tests: 5 passed;
- certified-domain regression tests: 18 passed;
- pre-certification full UIP suite: 1,260 passed, 1 existing warning;
- validation left the R1 worktree clean;
- fresh domain outputs certified by R1: false;
- real refreshed-data rehearsal performed by R1: false;
- production UIP database activation performed by R1: false;
- native domain models changed: false;
- cross-asset ranking authorized: false;
- allocation policy authorized: false;
- automatic execution authorized: false.

Permanent evidence:

`docs/project_control/generated/r1_refresh_orchestration/r1_refresh_orchestration_certification.json`

Regression protection:

`tests/test_r1_certification_evidence.py`

Disposition:

`UIP_R1_CERTIFIED_COMPLETE`

Active next milestone:

`UIP_R2_REFRESHED_DATA_REHEARSAL`

Expected following milestone:

`UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW`

R3 is a hard gate before E1 or dashboard decision logic. It evaluates fresh-output freshness/completeness, native self-consistency, distributions/outliers, change-from-prior plausibility, UIP semantic preservation, decision readiness, and investigation routing. R3 does not authorize cross-asset ranking or allocation.
"""
    _append_once(STATE, "## UIP-R1 certification closeout", section)


def close_ledger() -> None:
    text = _read(LEDGER)
    if "UIP-CHG-2026-032" in text:
        raise RuntimeError("Ledger entry UIP-CHG-2026-032 already exists.")
    marker = "---\n\n# Future change procedure"
    if text.count(marker) != 1:
        raise RuntimeError("Expected exactly one future-change ledger marker.")
    entry = """---

## UIP-CHG-2026-032 - Certify UIP-R1, Activate UIP-R2, and Establish UIP-R3 Health Gate

Date: 2026-08-14
Status: ACTIVE
Type: REFRESH_ORCHESTRATION, CERTIFICATION, ROADMAP_STATE, DOMAIN_HEALTH_GATE
Approval authority: Devon Lockard

Decision:

Certify `UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS` complete, activate `UIP_R2_REFRESHED_DATA_REHEARSAL`, and establish `UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW` as the required following gate before E1 or dashboard decision logic.

R1 evidence:

- governed main base: `55d5c72582bf70aff21a30b69edadab9ea9e8553`;
- technical contract head before certification evidence: `026169f85f411c4b76061a5c9e4b42de944efba4`;
- machine-readable contract: `config/orchestration/r1_domain_refresh_contracts.json`;
- typed interface: `foundation/orchestration/refresh_contracts.py`;
- human-readable contract: `docs/project_control/R1_REFRESH_ORCHESTRATION_CONTRACT.md`;
- domains governed: MTG, Metals, Crypto;
- required cycle evidence fields: 19;
- external-domain collection/model execution remains source-owned;
- direct UIP invocation of MTG/Crypto collectors remains prohibited;
- Metals remains UIP-native;
- failure preserves prior certified state and failed evidence;
- partial activation is prohibited;
- missing authority is not synthesized;
- permanent asset-population counts are prohibited;
- MTG refreshed hosted-delivery compatibility is not assumed and must be proven in R2;
- R1 focused tests: 5 passed;
- certified-domain regression tests: 18 passed;
- pre-certification full UIP suite: 1,260 passed, 1 existing warning;
- validation worktree remained clean.

R2 requirement:

R2 must execute real refreshed MTG, Metals, and Crypto cycles, capture the governed 19-field cycle evidence, use disposable UIP import state before any production activation, and prove current producer-output compatibility with the certified UIP domain bindings.

R3 requirement:

R3 must review each fresh domain across seven dimensions: freshness/completeness, native self-consistency, distribution/outliers, change-from-prior plausibility, UIP semantic preservation, decision readiness, and investigation routing.

Allowed R3 findings are `PASS`, `PASS_WITH_GOVERNED_GAPS`, `REVIEW`, and `DOMAIN_INVESTIGATION_REQUIRED`. A suspicious domain may be excluded from later UIP decision logic until its native authority is investigated and recertified. R3 does not create a universal rank, allocation methodology, or execution authority.

Permanent evidence:

`docs/project_control/generated/r1_refresh_orchestration/r1_refresh_orchestration_certification.json`

Regression protection:

`tests/test_r1_certification_evidence.py`

Prior state:

`UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS`

New state:

`UIP_R2_REFRESHED_DATA_REHEARSAL`

Expected following state:

`UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW`

Reversal:

`FULLY_REVERSIBLE`

Next required action:

`EXECUTE_REAL_REFRESHED_DATA_REHEARSAL`

---

# Future change procedure"""
    _write(LEDGER, text.replace(marker, entry, 1))


def main() -> int:
    close_start_here()
    close_roadmap()
    close_state()
    close_ledger()
    print("R1_GOVERNANCE_CLOSEOUT=PASS")
    print("NEXT_MILESTONE=UIP_R2_REFRESHED_DATA_REHEARSAL")
    print("FOLLOWING_MILESTONE=UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
