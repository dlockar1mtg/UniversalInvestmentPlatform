"""ETF (Merchants' Guild) records from the StocksETFIntelligencePlatform daily package.

The ETF repository publishes a manifest-governed package (its contracts/uip/package_manifest.schema.json)
as the `etf-production-<run>` artifact. The publication cycle downloads it, checks it with
`verify_etf_package`, and points UIP_ETF_PACKAGE_DIR at it. Prices come from free tier-4 sources,
so the package is PROVISIONAL, never certified, and its records sit beside the three certified
domains as their own record types (etf_fund, etf_package): the certified domain invariants
(health, asset surfaces, counts) are untouched.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

DOMAIN_ID = "etf"
REQUIRED_FILES = ("funds.json", "latest_prices.csv", "research.json", "market_data_status.json")
ALLOWED_CERTIFICATION = {"PROVISIONAL", "CERTIFIED"}
ALLOWED_VALIDATION = {"PASS", "PASS_WITH_LIMITATIONS"}
MANIFEST_KEYS = {"package_id", "domain", "contract_version", "generated_at_utc", "source_snapshot_id",
                 "repository_commit", "files", "validation_status", "certification_status",
                 "automatic_execution_authorized"}
_SHA = re.compile(r"^[0-9a-f]{64}$")


class ETFPackageError(RuntimeError):
    """Raised when an ETF package fails the UIP import contract."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_etf_package(directory: Path) -> dict[str, Any]:
    """Fail closed unless the manifest matches the contract and every file matches its digest."""
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        raise ETFPackageError("ETF package has no manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if set(manifest) != MANIFEST_KEYS:
        raise ETFPackageError(f"ETF manifest keys differ from the contract: {sorted(set(manifest) ^ MANIFEST_KEYS)}")
    if manifest["domain"] != "stocks_etf":
        raise ETFPackageError("ETF manifest is not for the stocks_etf domain")
    if not str(manifest["contract_version"]).startswith("1."):
        raise ETFPackageError(f"Unsupported ETF contract version {manifest['contract_version']}")
    if manifest["automatic_execution_authorized"] is not False:
        raise ETFPackageError("ETF package must not authorize automatic execution")
    if manifest["certification_status"] not in ALLOWED_CERTIFICATION:
        raise ETFPackageError(f"ETF package certification {manifest['certification_status']} is not importable")
    if manifest["validation_status"] not in ALLOWED_VALIDATION:
        raise ETFPackageError(f"ETF package validation {manifest['validation_status']} is not importable")
    listed = {}
    for item in manifest["files"]:
        path = str(item.get("path") or "")
        if not path or "/" in path or "\\" in path or path.startswith("."):
            raise ETFPackageError(f"ETF package file path is not allowed: {path!r}")
        if not _SHA.fullmatch(str(item.get("sha256") or "")):
            raise ETFPackageError(f"ETF package digest is invalid for {path}")
        target = directory / path
        if not target.is_file() or _sha256(target) != item["sha256"]:
            raise ETFPackageError(f"ETF package file missing or digest mismatch: {path}")
        listed[path] = item
    missing = [name for name in REQUIRED_FILES if name not in listed]
    if missing:
        raise ETFPackageError(f"ETF package is missing {missing}")
    funds = json.loads((directory / "funds.json").read_text(encoding="utf-8"))
    if listed["funds.json"]["row_count"] != len(funds.get("funds") or []):
        raise ETFPackageError("ETF funds.json row count differs from the manifest")
    if funds.get("automatic_execution_authorized") is not False:
        raise ETFPackageError("ETF funds document must not authorize automatic execution")
    return manifest


def build_etf_records(directory: Path, *, source_run_id: str | None = None):
    from .publication_model import PresentationRecord

    manifest = verify_etf_package(directory)
    funds = json.loads((directory / "funds.json").read_text(encoding="utf-8"))
    research = json.loads((directory / "research.json").read_text(encoding="utf-8"))
    lineage = {"package_id": manifest["package_id"], "package_as_of": funds.get("as_of_date"),
               "certification_status": manifest["certification_status"],
               "validation_status": manifest["validation_status"],
               "source_repository": "dlockar1mtg/StocksETFIntelligencePlatform",
               "source_commit": manifest["repository_commit"], "source_run_id": source_run_id}
    records = []
    for fund in funds["funds"]:
        ticker = str(fund["ticker"]).upper()
        records.append(PresentationRecord("etf_fund", DOMAIN_ID, f"etf:{ticker.lower()}", ticker,
                                          {**fund, "_lineage": lineage, "automatic_execution_authorized": False}))
    records.append(PresentationRecord("etf_package", DOMAIN_ID, None, "etf-v1", {
        **lineage, "generated_at_utc": manifest["generated_at_utc"], "model_version": funds.get("model_version"),
        "limitations": funds.get("limitations") or [], "fund_count": len(funds["funds"]),
        "research": research, "automatic_execution_authorized": False,
    }))
    return records


def etf_records_from_environment():
    """ETF records when the publication cycle supplied a verified package; none otherwise."""
    raw = str(os.environ.get("UIP_ETF_PACKAGE_DIR", "")).strip()
    if not raw:
        return []
    return build_etf_records(Path(raw), source_run_id=os.environ.get("UIP_ETF_SOURCE_RUN_ID") or None)


def main(argv: list[str] | None = None) -> int:
    """`python -m foundation.presentation.etf_package DIR` verifies a downloaded package."""
    import sys

    args = sys.argv[1:] if argv is None else argv
    manifest = verify_etf_package(Path(args[0]))
    print(f"{manifest['package_id']} {manifest['validation_status']} {manifest['certification_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
