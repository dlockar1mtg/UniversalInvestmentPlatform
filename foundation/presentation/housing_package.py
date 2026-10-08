"""Housing records from the HousingIntelligencePlatform weekly package (housing_uip_contract.json).

The housing repository publishes a manifest plus one contract file as the `housing-production-<run>`
artifact. The publication cycle downloads it, checks it with `verify_housing_package`, and points
UIP_HOUSING_PACKAGE_DIR at it. The package is PROVISIONAL and carries market facts only (the household
side lives in the UIP's household plan); its records sit beside the certified domains as their own
record types (housing_market, housing_package) without touching the certified invariants.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

DOMAIN_ID = "housing"
CONTRACT_FILE = "housing_uip_contract.json"
MANIFEST_KEYS = {"package_id", "domain", "contract_version", "generated_at_utc", "repository_commit", "files",
                 "validation_status", "certification_status", "automatic_execution_authorized"}
SIGNALS = {"Strong Buy", "Buy", "Slight Buy", "Neutral / Fair Value", "Slight Wait", "Wait", "Strong Wait / High Risk"}
_SHA = re.compile(r"^[0-9a-f]{64}$")


class HousingPackageError(RuntimeError):
    """Raised when a housing package fails the UIP import contract."""


def verify_housing_package(directory: Path) -> dict[str, Any]:
    """Fail closed unless the manifest, the digest and the contract all check out. Returns the contract."""
    directory = Path(directory)
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        raise HousingPackageError("housing package has no manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if set(manifest) != MANIFEST_KEYS:
        raise HousingPackageError(f"housing manifest keys differ from the contract: {sorted(set(manifest) ^ MANIFEST_KEYS)}")
    if manifest["domain"] != DOMAIN_ID or not str(manifest["contract_version"]).startswith("1."):
        raise HousingPackageError("housing manifest domain or contract version is not importable")
    if manifest["automatic_execution_authorized"] is not False:
        raise HousingPackageError("housing package must not authorize automatic execution")
    if manifest["validation_status"] != "PASS" or manifest["certification_status"] not in ("PROVISIONAL", "CERTIFIED"):
        raise HousingPackageError("housing package status is not importable")
    files = {f.get("path"): f for f in manifest["files"]}
    item = files.get(CONTRACT_FILE)
    if not item or not _SHA.fullmatch(str(item.get("sha256") or "")):
        raise HousingPackageError("housing manifest does not list the contract with a digest")
    target = directory / CONTRACT_FILE
    if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != item["sha256"]:
        raise HousingPackageError("housing contract missing or digest mismatch")
    contract = json.loads(target.read_text(encoding="utf-8"))
    if contract.get("domain") != DOMAIN_ID or not str(contract.get("contract_version", "")).startswith("1."):
        raise HousingPackageError("housing contract domain or version is not importable")
    if contract.get("automatic_execution_authorized") is not False or contract.get("household") is not None:
        raise HousingPackageError("housing contract must carry no household data and no execution authority")
    markets = contract.get("markets") or []
    if not markets or item.get("row_count") != len(markets):
        raise HousingPackageError("housing contract market count differs from the manifest")
    for m in markets:
        if m.get("signal") not in SIGNALS or not 0 <= float(m.get("entry_score", -1)) <= 100 or not m.get("market_state_as_of"):
            raise HousingPackageError(f"housing market {m.get('market')!r} fails the contract")
    return {"manifest": manifest, "contract": contract}


def build_housing_records(directory: Path, *, source_run_id: str | None = None):
    from .publication_model import PresentationRecord

    checked = verify_housing_package(directory)
    manifest, contract = checked["manifest"], checked["contract"]
    lineage = {"package_id": manifest["package_id"], "certification_status": manifest["certification_status"],
               "generated_at_utc": contract["generated_at_utc"], "model_version": contract.get("model_version"),
               "source_repository": contract.get("source_repository"), "source_commit": contract.get("source_commit"),
               "source_run_id": source_run_id or contract.get("source_run_id")}
    records = []
    for market in contract["markets"]:
        key = re.sub(r"[^a-z0-9]+", "-", str(market["market"]).lower()).strip("-")
        records.append(PresentationRecord("housing_market", DOMAIN_ID, f"housing:{key}", key,
                                          {**market, "_lineage": lineage, "automatic_execution_authorized": False}))
    records.append(PresentationRecord("housing_package", DOMAIN_ID, None, "housing-markets", {
        **lineage, "contract_version": contract["contract_version"], "data_freshness": contract.get("data_freshness") or {},
        "latest_input_observation": contract.get("latest_input_observation"), "known_issues": contract.get("known_issues") or [],
        "warnings": contract.get("warnings") or [], "market_count": len(contract["markets"]),
        "automatic_execution_authorized": False}))
    return records


def housing_records_from_environment():
    """Housing records when the publication cycle supplied a verified package; none otherwise."""
    raw = str(os.environ.get("UIP_HOUSING_PACKAGE_DIR", "")).strip()
    if not raw:
        return []
    return build_housing_records(Path(raw), source_run_id=os.environ.get("UIP_HOUSING_SOURCE_RUN_ID") or None)


def main(argv: list[str] | None = None) -> int:
    """`python -m foundation.presentation.housing_package DIR` verifies a downloaded package."""
    import sys

    args = sys.argv[1:] if argv is None else argv
    checked = verify_housing_package(Path(args[0]))
    m = checked["manifest"]
    print(f"{m['package_id']} {m['validation_status']} {m['certification_status']} "
          + " | ".join(f"{x['market']} {x['entry_score']:.1f} {x['signal']} as of {x['market_state_as_of']}" for x in checked["contract"]["markets"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
