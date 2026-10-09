"""Macro records from the MacroIntelligencePlatform daily package (macro_uip_contract.json).

The macro repository publishes a manifest plus one contract file as the `macro-production-<run>` artifact.
The publication cycle downloads it, checks it with `verify_macro_package`, and points UIP_MACRO_PACKAGE_DIR
at it. The package is PROVISIONAL: the Composite Recession Stress Index (RSI v2.0) with its components,
history, evaluation and the earlier analyst readings (kept, marked unverified). It informs; it never
changes holdings, recommendations or allocations.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

DOMAIN_ID = "macro"
CONTRACT_FILE = "macro_uip_contract.json"
MANIFEST_KEYS = {"package_id", "domain", "contract_version", "generated_at_utc", "repository_commit", "files",
                 "validation_status", "certification_status", "automatic_execution_authorized"}
BANDS = {"EXPANSION", "LATE_CYCLE", "DETERIORATION", "RECESSIONARY_STRESS", "PANIC"}
_SHA = re.compile(r"^[0-9a-f]{64}$")


class MacroPackageError(RuntimeError):
    """Raised when a macro package fails the UIP import contract."""


def verify_macro_package(directory: Path) -> dict[str, Any]:
    """Fail closed unless the manifest, the digest and the contract all check out."""
    directory = Path(directory)
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        raise MacroPackageError("macro package has no manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if set(manifest) != MANIFEST_KEYS:
        raise MacroPackageError(f"macro manifest keys differ from the contract: {sorted(set(manifest) ^ MANIFEST_KEYS)}")
    if manifest["domain"] != DOMAIN_ID or not str(manifest["contract_version"]).startswith("1."):
        raise MacroPackageError("macro manifest domain or contract version is not importable")
    if manifest["automatic_execution_authorized"] is not False:
        raise MacroPackageError("macro package must not authorize automatic execution")
    if manifest["validation_status"] != "PASS" or manifest["certification_status"] not in ("PROVISIONAL", "CERTIFIED"):
        raise MacroPackageError("macro package status is not importable")
    item = {f.get("path"): f for f in manifest["files"]}.get(CONTRACT_FILE)
    if not item or not _SHA.fullmatch(str(item.get("sha256") or "")):
        raise MacroPackageError("macro manifest does not list the contract with a digest")
    target = directory / CONTRACT_FILE
    if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != item["sha256"]:
        raise MacroPackageError("macro contract missing or digest mismatch")
    c = json.loads(target.read_text(encoding="utf-8"))
    if c.get("domain") != DOMAIN_ID or not str(c.get("contract_version", "")).startswith("1.") or c.get("automatic_execution_authorized") is not False:
        raise MacroPackageError("macro contract domain, version or authority is not importable")
    cur = c.get("current") or {}
    if cur.get("rsi") is not None:
        if not -1 <= float(cur["rsi"]) <= 1 or cur.get("band") not in BANDS:
            raise MacroPackageError("macro rsi out of range or unknown band")
        if abs(sum(float(r.get("contribution") or 0) for r in cur.get("components") or []) - float(cur["rsi"])) > 0.002:
            raise MacroPackageError("macro component contributions do not add up to the rsi")
    if any(not s.get("legacy_unverified") for s in c.get("legacy_snapshots") or []):
        raise MacroPackageError("legacy analyst readings must stay marked unverified")
    if (c.get("recession_probability") or {}).get("status") == "PUBLISHED" and not c["recession_probability"].get("calibration"):
        raise MacroPackageError("a recession probability needs its calibration evidence")
    if item.get("row_count") != len(c.get("history") or []):
        raise MacroPackageError("macro history length differs from the manifest")
    return {"manifest": manifest, "contract": c}


def build_macro_records(directory: Path, *, source_run_id: str | None = None):
    from .publication_model import PresentationRecord

    checked = verify_macro_package(directory)
    manifest, c = checked["manifest"], checked["contract"]
    lineage = {"package_id": manifest["package_id"], "certification_status": manifest["certification_status"],
               "generated_at_utc": c["generated_at_utc"], "model_id": c.get("model_id"), "model_version": c.get("model_version"),
               "source_repository": c.get("source_repository"), "source_commit": c.get("source_commit"),
               "source_run_id": source_run_id or c.get("source_run_id"), "contract_version": c["contract_version"]}
    current = {**(c.get("current") or {}), "_lineage": lineage, "automatic_execution_authorized": False}
    package = {**lineage, "weights": c.get("weights"), "anchors": c.get("anchors"), "bands": c.get("bands"),
               "bands_status": c.get("bands_status"), "history": c.get("history") or [], "evaluation": c.get("evaluation"),
               "legacy_snapshots": c.get("legacy_snapshots") or [], "data_freshness": c.get("data_freshness") or {},
               "recession_probability": c.get("recession_probability"), "asset_environment": c.get("asset_environment"),
               "housing_opportunity": c.get("housing_opportunity"), "automatic_execution_authorized": False}
    return [PresentationRecord("macro_reading", DOMAIN_ID, None, "rsi-current", current),
            PresentationRecord("macro_package", DOMAIN_ID, None, "macro-rsi", package)]


def macro_records_from_environment():
    raw = str(os.environ.get("UIP_MACRO_PACKAGE_DIR", "")).strip()
    if not raw:
        return []
    return build_macro_records(Path(raw), source_run_id=os.environ.get("UIP_MACRO_SOURCE_RUN_ID") or None)


def main(argv: list[str] | None = None) -> int:
    """`python -m foundation.presentation.macro_package DIR` verifies a downloaded package."""
    import sys

    args = sys.argv[1:] if argv is None else argv
    checked = verify_macro_package(Path(args[0]))
    m, cur = checked["manifest"], checked["contract"].get("current") or {}
    print(f"{m['package_id']} {m['validation_status']} {m['certification_status']} RSI {cur.get('rsi')} {cur.get('band')} "
          f"as of {cur.get('as_of_month')} coverage {cur.get('coverage')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
