"""Read-only audit of whether latest source artifacts can reproduce the rich UIP presentation.

No database connection is opened and no publication is staged or activated.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


EXPECTED_MTG = {
    "premium": ("docs/phase_9/uip_export/premium_research/mtg_secret_lair_premium_research.csv", 787),
    "collector": ("docs/phase_9/uip_export/research_sidecars/mtg_collector_research.csv", 50),
    "collector_horizon": ("docs/phase_9/uip_export/research_sidecars/mtg_collector_forecast_horizon.csv", 294),
    "precollector": ("docs/phase_9/uip_export/research_sidecars/mtg_precollector_research.csv", 131),
    "precollector_scenario": ("docs/phase_9/uip_export/research_sidecars/mtg_precollector_scenario_horizon.csv", 190),
}

# These record families are present in the restored 13,929-record publication and therefore
# must have an explicit fresh source contract before production activation can be re-enabled.
REQUIRED_METALS_RICH_FAMILIES = {
    "price_history": ("metals_price_history", 1),
    "current_price": ("metals_current_price", 1),
    "data_freshness": ("metals_data_freshness", 1),
    "model_component": ("metals_model_component", 1),
    "platform_health": ("metals_platform_health", 1),
    "recommendation_change": ("metals_recommendation_change", 1),
    "regime_probability": ("metals_regime_probability", 1),
    "uncertainty_adjusted": ("metals_uncertainty_adjusted", 1),
    "tactical_state": ("tactical_state", 1),
    "risk": ("risk", 1),
}


def csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.reader(handle)) - 1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metals-artifact", type=Path, required=True)
    parser.add_argument("--mtg-repo", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path, required=True)
    args = parser.parse_args()

    metals_root = args.metals_artifact.resolve()
    mtg_root = args.mtg_repo.resolve()
    if not metals_root.is_dir():
        raise RuntimeError(f"Metals artifact root missing: {metals_root}")
    if not mtg_root.is_dir():
        raise RuntimeError(f"MTG checkout missing: {mtg_root}")

    mtg = {}
    mtg_pass = True
    for key, (relative, expected_rows) in EXPECTED_MTG.items():
        path = mtg_root / relative
        exists = path.is_file()
        rows = csv_rows(path) if exists else None
        passed = exists and rows == expected_rows
        mtg_pass = mtg_pass and passed
        mtg[key] = {
            "path": relative,
            "exists": exists,
            "rows": rows,
            "expected_rows": expected_rows,
            "sha256": sha256(path) if exists else None,
            "pass": passed,
        }

    files = inventory(metals_root)
    lower_files = [name.lower() for name in files]
    metals_families = {}
    metals_pass = True
    for key, (needle, minimum) in REQUIRED_METALS_RICH_FAMILIES.items():
        matches = [name for name in files if needle in name.lower()]
        passed = len(matches) >= minimum
        metals_pass = metals_pass and passed
        metals_families[key] = {
            "needle": needle,
            "matches": matches,
            "pass": passed,
        }

    evidence = {
        "status": "PASS" if mtg_pass and metals_pass else "FAIL_CLOSED",
        "postgres_write_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "mtg_rich_source_contract_pass": mtg_pass,
        "mtg": mtg,
        "metals_rich_source_contract_pass": metals_pass,
        "metals_required_families": metals_families,
        "metals_artifact_file_count": len(files),
        "metals_artifact_files": files,
        "failure_policy": "NO_PRODUCTION_PUBLICATION_UNTIL_RICH_SOURCE_CONTRACTS_ARE_REPRODUCIBLE",
    }

    output = args.evidence_output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
