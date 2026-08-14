from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START = ROOT / "docs" / "project_control" / "00_START_HERE.md"
ROADMAP = ROOT / "docs" / "project_control" / "04_ACTIVE_ROADMAP.md"
STATE = ROOT / "docs" / "project_control" / "05_PROJECT_STATE.md"
LEDGER = ROOT / "docs" / "project_control" / "06_CHANGE_LEDGER.md"


def read_text(path: Path) -> tuple[str, str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        text = handle.read()
    newline = "\r\n" if "\r\n" in text else "\n"
    return text, newline


def write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def adapt(value: str, newline: str) -> str:
    return value.replace("\n", newline)


def replace_once(path: Path, old: str, new: str) -> None:
    text, newline = read_text(path)
    old_value = adapt(old, newline)
    new_value = adapt(new, newline)
    count = text.count(old_value)
    if count != 1:
        raise RuntimeError(
            f"Expected one anchor in {path}; found {count}: {old!r}"
        )
    write_text(path, text.replace(old_value, new_value, 1))


def append_once(path: Path, marker: str, section: str) -> None:
    text, newline = read_text(path)
    if marker in text:
        raise RuntimeError(f"Section already exists in {path}: {marker}")
    if not text.endswith(newline):
        text += newline
    write_text(path, text + adapt(section, newline) + newline)


replace_once(
    START,
    "Current governed main baseline:\n\n"
    "`398f949dee1f6af76d7823f07f61c628fab1ca57`",
    "Current governed main baseline:\n\n"
    "`1babdacdc101e40f6f4550b56883ccc7b2d0f674`",
)
replace_once(
    START,
    "Current next authorized action:\n\n"
    "`UIP_D1_COMMON_DOMAIN_REGISTRY_AND_LINEAGE_INTERFACE`",
    "Current next authorized action:\n\n"
    "`UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS`",
)
replace_once(
    START,
    "The controlled recovery evidence remains preserved. Under "
    "`UIP-CHG-2026-026` through `UIP-CHG-2026-030`, MTG, Metals, and "
    "Crypto certified-domain integration milestones are complete. The "
    "active next action is the common UIP domain registry and lineage "
    "interface. Certified native-domain work must not be reopened without "
    "a verified governance defect.",
    "The controlled recovery evidence remains preserved. Under "
    "`UIP-CHG-2026-026` through `UIP-CHG-2026-031`, MTG, Metals, Crypto, "
    "and D1 are certified complete. The active next action is R1 governed "
    "refresh and orchestration contracts. Certified native-domain and D1 "
    "work must not be reopened without a verified governance defect.",
)

replace_once(
    ROADMAP,
    "- `UIP_CRYPTO_A0_A1_DOMAIN_BINDING`\n",
    "- `UIP_CRYPTO_A0_A1_DOMAIN_BINDING`\n"
    "- `UIP_D1_COMMON_DOMAIN_REGISTRY_AND_LINEAGE_INTERFACE`\n",
)
replace_once(
    ROADMAP,
    "Current milestone:\n\n"
    "`UIP_D1_COMMON_DOMAIN_REGISTRY_AND_LINEAGE_INTERFACE`\n\n"
    "Next authorized action:\n\n"
    "`IMPLEMENT_COMMON_DOMAIN_REGISTRY_AND_LINEAGE_INTERFACE`\n\n"
    "Expected subsequent action:\n\n"
    "`UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS`",
    "Current milestone:\n\n"
    "`UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS`\n\n"
    "Next authorized action:\n\n"
    "`IMPLEMENT_REFRESH_AND_ORCHESTRATION_CONTRACTS`\n\n"
    "Expected subsequent action:\n\n"
    "`UIP_R2_REFRESHED_DATA_REHEARSAL`",
)

replace_once(
    STATE,
    "Current milestone:\n"
    "UIP_D1_COMMON_DOMAIN_REGISTRY_AND_LINEAGE_INTERFACE",
    "Current milestone:\n"
    "UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS",
)
replace_once(
    STATE,
    "Next authorized action:\n"
    "UIP_D1_COMMON_DOMAIN_REGISTRY_AND_LINEAGE_INTERFACE",
    "Next authorized action:\n"
    "UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS",
)
replace_once(
    STATE,
    "Current governed main baseline:\n\n"
    "`398f949dee1f6af76d7823f07f61c628fab1ca57`",
    "Current governed main baseline:\n\n"
    "`1babdacdc101e40f6f4550b56883ccc7b2d0f674`",
)
replace_once(
    STATE,
    "Active governance branch:\n\n"
    "`phase-uip-crypto-a0-a1-domain-binding`",
    "Active governance branch:\n\n"
    "`phase-uip-d1-common-domain-registry`",
)
replace_once(
    STATE,
    "Active next milestone:\n\n"
    "`UIP_D1_COMMON_DOMAIN_REGISTRY_AND_LINEAGE_INTERFACE`",
    "Active next milestone:\n\n"
    "`UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS`",
)

state_section = "\n".join(
    [
        "",
        "## UIP-D1 certification closeout",
        "",
        "D1 status:",
        "",
        "`UIP_D1_COMMON_DOMAIN_REGISTRY_AND_LINEAGE_CERTIFICATION_PASS`",
        "",
        "Certified implementation commit:",
        "",
        "`9a1f011cb92069069f54967442bbf3d6d0ea281c`",
        "",
        "Certified authority and controls:",
        "",
        "- canonical registry authority: `foundation/import_engine/sql/006_common_domain_registry_lineage.sql`;",
        "- certified domains: MTG, Metals, Crypto;",
        "- fresh canonical databases initialize the registry automatically;",
        "- Python domain-registry access is read-only and unknown domains fail closed;",
        "- native domain semantics remain authoritative;",
        "- permanent asset-population counts are not stored;",
        "- common lineage preserves import, package, source-file, source-row, manifest, and import-time evidence;",
        "- MTG native authority is included without flattening native ranking or purchase semantics;",
        "- canonical migrations: 001 through 006;",
        "- canonical database objects: 31;",
        "- D1 schema objects: 4;",
        "- focused D1 tests: 5 passed;",
        "- migration tests: 5 passed;",
        "- combined D1/schema tests: 10 passed;",
        "- full UIP suite: 1,251 passed, 1 existing warning;",
        "- production UIP database modified: false;",
        "- native domain databases modified: false;",
        "- cross-asset ranking created: false;",
        "- allocation policy created: false;",
        "- automatic purchase execution created: false.",
        "",
        "Permanent evidence:",
        "",
        "`docs/project_control/generated/d1_common_domain_registry/d1_common_domain_registry_certification.json`",
        "",
        "Regression protection:",
        "",
        "`tests/test_d1_certification_evidence.py`",
        "",
        "Disposition:",
        "",
        "`UIP_D1_CERTIFIED_COMPLETE`",
        "",
        "Active next milestone:",
        "",
        "`UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS`",
    ]
)
append_once(STATE, "## UIP-D1 certification closeout", state_section)

ledger_text, ledger_newline = read_text(LEDGER)
if "UIP-CHG-2026-031" in ledger_text:
    raise RuntimeError("Ledger entry UIP-CHG-2026-031 already exists.")

ledger_marker = adapt("---\n\n# Future change procedure", ledger_newline)
if ledger_text.count(ledger_marker) != 1:
    raise RuntimeError("Unable to locate unique change-ledger insertion marker.")

ledger_entry = "\n".join(
    [
        "---",
        "",
        "## UIP-CHG-2026-031 - Certify UIP-D1 and Activate UIP-R1",
        "",
        "Date: 2026-08-14",
        "Status: ACTIVE",
        "Type: COMMON_DOMAIN_REGISTRY, LINEAGE, CERTIFICATION, ROADMAP_STATE",
        "Approval authority: Devon Lockard",
        "",
        "Decision:",
        "",
        "Certify `UIP_D1_COMMON_DOMAIN_REGISTRY_AND_LINEAGE_INTERFACE` complete and activate",
        "`UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS`.",
        "",
        "D1 evidence:",
        "",
        "- certified implementation commit: `9a1f011cb92069069f54967442bbf3d6d0ea281c`;",
        "- canonical registry authority: `foundation/import_engine/sql/006_common_domain_registry_lineage.sql`;",
        "- certified domains: MTG, Metals, Crypto;",
        "- canonical certified-domain count: 3;",
        "- fresh canonical databases initialize the registry automatically;",
        "- Python registry access is read-only and unknown domains fail closed;",
        "- native domain semantics remain authoritative;",
        "- permanent asset-population counts are not embedded;",
        "- common row lineage spans certified universal histories plus MTG native authority;",
        "- canonical migration chain: 001 through 006;",
        "- canonical schema object count: 31;",
        "- D1 schema object count: 4;",
        "- schema-control generation and validate-only validation: pass;",
        "- focused D1 tests: 5 passed;",
        "- migration tests: 5 passed;",
        "- combined D1/schema tests: 10 passed;",
        "- full UIP suite: 1,251 passed, 1 existing warning;",
        "- production UIP database modified: false;",
        "- native domain databases modified: false;",
        "- cross-asset ranking created: false;",
        "- allocation policy created: false;",
        "- automatic purchase execution created: false.",
        "",
        "Permanent evidence:",
        "",
        "`docs/project_control/generated/d1_common_domain_registry/d1_common_domain_registry_certification.json`",
        "",
        "Regression protection:",
        "",
        "`tests/test_d1_certification_evidence.py`",
        "",
        "Governance effect:",
        "",
        "UIP now has one governed common domain registry and one common lineage interface for the three certified domains.",
        "R1 may define refresh and orchestration contracts against this interface without reopening native domain semantics.",
        "",
        "No universal cross-asset ranking, comparison methodology, allocation policy, or automatic trade execution is authorized.",
        "",
        "Prior state:",
        "",
        "`UIP_D1_COMMON_DOMAIN_REGISTRY_AND_LINEAGE_INTERFACE`",
        "",
        "New state:",
        "",
        "`UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS`",
        "",
        "Reversal:",
        "",
        "`FULLY_REVERSIBLE`",
        "",
        "Next required action:",
        "",
        "`IMPLEMENT_REFRESH_AND_ORCHESTRATION_CONTRACTS`",
        "",
    ]
)
write_text(
    LEDGER,
    ledger_text.replace(
        ledger_marker,
        adapt(ledger_entry, ledger_newline) + ledger_marker,
        1,
    ),
)

for path in (START, ROADMAP, STATE, LEDGER):
    text, _ = read_text(path)
    for forbidden in ("â†’", "â€”", "ï»¿"):
        if forbidden in text:
            raise RuntimeError(f"Mojibake detected in {path}: {forbidden}")

print("D1_GOVERNANCE_CLOSEOUT=PASS")
print("NEXT_MILESTONE=UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS")
