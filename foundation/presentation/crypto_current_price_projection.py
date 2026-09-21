"""Project the governed Crypto Current Price V1 sidecar into presentation records."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from foundation.presentation.publication_model import PresentationRecord

AUTHORITY_ID = "CRYPTO_CANONICAL_MARKET_DAILY_CURRENT_PRICE_V1"
SCHEMA_VERSION = "1.0.0"
METHODOLOGY_VERSION = "1.0.0"
SCOPE = "SIX_ASSET_LATEST_DAILY_CANONICAL_MARKET_PRICE"
SOURCE_TABLE = "canonical_market_daily"
PRICE_SEMANTICS = "DAILY_CANONICAL_MARKET_CLOSE"
PRESENTATION_SEMANTICS = "CURRENT_PRICE_FOR_PORTFOLIO_VALUATION_NOT_EXECUTION_QUOTE"
RECORD_TYPE = "crypto_current_price"
SUPPORTED_ASSETS = (
    "crypto:bitcoin",
    "crypto:ethereum",
    "crypto:solana",
    "crypto:chainlink",
    "crypto:xrp",
    "crypto:avalanche",
)
NATIVE_ASSET_IDS = {
    "crypto:bitcoin": "bitcoin",
    "crypto:ethereum": "ethereum",
    "crypto:solana": "solana",
    "crypto:chainlink": "chainlink",
    "crypto:xrp": "xrp",
    "crypto:avalanche": "avalanche",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_sidecars(root: Path) -> tuple[Path, Path]:
    manifests = sorted(root.rglob("crypto_current_price_v1_manifest.json"))
    csvs = sorted(root.rglob("crypto_current_price_v1.csv"))
    if len(manifests) != 1 or len(csvs) != 1:
        raise RuntimeError(
            "Crypto Current Price V1 artifact must contain exactly one CSV and one manifest: "
            f"csvs={len(csvs)} manifests={len(manifests)}"
        )
    if manifests[0].parent != csvs[0].parent:
        raise RuntimeError("Crypto Current Price V1 CSV and manifest must share one delivery directory")
    return csvs[0], manifests[0]


def audit_crypto_current_price_v1(root: Path) -> dict[str, object]:
    csv_path, manifest_path = _resolve_sidecars(root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    observed_assets = tuple(row.get("universal_asset_id", "") for row in rows)
    checks = {
        "manifest_status": manifest.get("status") == "CRYPTO_CURRENT_PRICE_V1_PASS",
        "authority_id": manifest.get("authority_id") == AUTHORITY_ID,
        "schema_version": manifest.get("schema_version") == SCHEMA_VERSION,
        "methodology_version": manifest.get("methodology_version") == METHODOLOGY_VERSION,
        "scope": manifest.get("scope") == SCOPE,
        "source_table": manifest.get("source_table") == SOURCE_TABLE,
        "row_count": manifest.get("row_count") == len(SUPPORTED_ASSETS) == len(rows),
        "supported_assets": tuple(manifest.get("supported_assets") or ()) == SUPPORTED_ASSETS,
        "price_semantics": manifest.get("price_semantics") == PRICE_SEMANTICS,
        "presentation_semantics": manifest.get("presentation_semantics") == PRESENTATION_SEMANTICS,
        "output_sha256": manifest.get("output_sha256") == _sha256(csv_path),
        "forecast_not_reused": manifest.get("forecast_input_reused_as_price_authority") is False,
        "intraday_quote_not_claimed": manifest.get("intraday_quote_claimed") is False,
        "execution_authority_not_granted": manifest.get("execution_authority_granted") is False,
        "exact_asset_order": observed_assets == SUPPORTED_ASSETS,
    }

    seen: set[str] = set()
    for row in rows:
        universal_id = str(row.get("universal_asset_id") or "")
        if universal_id in seen:
            checks[f"unique_{universal_id}"] = False
            continue
        seen.add(universal_id)
        expected_native = NATIVE_ASSET_IDS.get(universal_id)
        try:
            price = float(row.get("current_price_usd") or "")
        except ValueError:
            price = -1.0
        try:
            priority = int(row.get("source_priority") or "")
        except ValueError:
            priority = 0
        checks[f"row_{universal_id}"] = all(
            (
                expected_native is not None,
                row.get("asset_id") == expected_native,
                bool(row.get("observation_date")),
                price > 0,
                bool(row.get("price_source")),
                priority >= 1,
                bool(row.get("collected_at_utc")),
                row.get("source_table") == SOURCE_TABLE,
                row.get("authority_id") == AUTHORITY_ID,
                row.get("schema_version") == SCHEMA_VERSION,
                row.get("methodology_version") == METHODOLOGY_VERSION,
                row.get("price_semantics") == PRICE_SEMANTICS,
                row.get("presentation_semantics") == PRESENTATION_SEMANTICS,
            )
        )

    return {
        "pass": all(checks.values()),
        "csv": str(csv_path.relative_to(root)),
        "manifest": str(manifest_path.relative_to(root)),
        "rows": len(rows),
        "sha256": _sha256(csv_path),
        "checks": checks,
    }


def build_crypto_current_price_records(root: Path) -> tuple[PresentationRecord, ...]:
    audit = audit_crypto_current_price_v1(root)
    if not audit["pass"]:
        failed = [key for key, value in audit["checks"].items() if not value]
        raise RuntimeError(f"Crypto Current Price V1 failed source contract: {failed}")

    csv_path, _ = _resolve_sidecars(root)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    return tuple(
        PresentationRecord(
            record_type=RECORD_TYPE,
            domain_id="crypto",
            asset_id=str(row["universal_asset_id"]),
            record_key=str(row["universal_asset_id"]),
            payload=dict(row),
        )
        for row in rows
    )
