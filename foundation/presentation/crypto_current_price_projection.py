"""Project certified Crypto Current Price V1 sidecar into presentation records.

This module is read-only. It consumes the source-owned Crypto production artifact,
validates the exact current-price authority contract, and returns presentation records.
It performs no persistence and grants no execution authority.
"""
from __future__ import annotations

import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

from foundation.presentation.publication_model import PresentationRecord

DOMAIN_ID = "crypto"
RECORD_TYPE = "crypto_current_price"
AUTHORITY_ID = "CRYPTO_CANONICAL_MARKET_DAILY_CURRENT_PRICE_V1"
SCHEMA_VERSION = "1.0.0"
METHODOLOGY_VERSION = "1.0.0"
SOURCE_TABLE = "canonical_market_daily"
PRICE_SEMANTICS = "DAILY_CANONICAL_MARKET_CLOSE"
PRESENTATION_SEMANTICS = "CURRENT_PRICE_FOR_PORTFOLIO_VALUATION_NOT_EXECUTION_QUOTE"
SUPPORTED_ASSETS = (
    "crypto:bitcoin",
    "crypto:ethereum",
    "crypto:solana",
    "crypto:chainlink",
    "crypto:xrp",
    "crypto:avalanche",
)
CSV_NAME = "crypto_current_price_v1.csv"
MANIFEST_NAME = "crypto_current_price_v1_manifest.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _exact_file(root: Path, name: str) -> Path:
    matches = sorted(path for path in root.rglob(name) if path.is_file())
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one certified Crypto current-price file named {name}; "
            f"observed={len(matches)}"
        )
    return matches[0]


def build_crypto_current_price_records(artifact_root: Path) -> list[PresentationRecord]:
    root = artifact_root.resolve()
    csv_path = _exact_file(root, CSV_NAME)
    manifest_path = _exact_file(root, MANIFEST_NAME)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_manifest = {
        "status": "CRYPTO_CURRENT_PRICE_V1_PASS",
        "authority_id": AUTHORITY_ID,
        "schema_version": SCHEMA_VERSION,
        "methodology_version": METHODOLOGY_VERSION,
        "scope": "SIX_ASSET_LATEST_DAILY_CANONICAL_MARKET_PRICE",
        "source_table": SOURCE_TABLE,
        "row_count": 6,
        "supported_assets": list(SUPPORTED_ASSETS),
        "price_semantics": PRICE_SEMANTICS,
        "presentation_semantics": PRESENTATION_SEMANTICS,
        "forecast_input_reused_as_price_authority": False,
        "intraday_quote_claimed": False,
        "execution_authority_granted": False,
    }
    for key, expected in expected_manifest.items():
        if manifest.get(key) != expected:
            raise RuntimeError(
                f"Crypto current-price manifest mismatch for {key}: "
                f"expected={expected!r} observed={manifest.get(key)!r}"
            )
    if manifest.get("output_sha256") != _sha256(csv_path):
        raise RuntimeError("Crypto current-price CSV SHA-256 does not match its certified manifest")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 6:
        raise RuntimeError(f"Expected exactly 6 Crypto current-price rows, observed {len(rows)}")

    records: list[PresentationRecord] = []
    seen: set[str] = set()
    for row in rows:
        universal_asset_id = str(row.get("universal_asset_id") or "").strip()
        native_asset_id = str(row.get("asset_id") or "").strip()
        if universal_asset_id not in SUPPORTED_ASSETS:
            raise RuntimeError(f"Unexpected Crypto current-price asset: {universal_asset_id}")
        if universal_asset_id in seen:
            raise RuntimeError(f"Duplicate Crypto current-price asset: {universal_asset_id}")
        if universal_asset_id != f"crypto:{native_asset_id}":
            raise RuntimeError(f"Crypto current-price identity mismatch: {universal_asset_id}")
        if row.get("authority_id") != AUTHORITY_ID:
            raise RuntimeError(f"Crypto current-price authority mismatch: {universal_asset_id}")
        if row.get("schema_version") != SCHEMA_VERSION:
            raise RuntimeError(f"Crypto current-price schema mismatch: {universal_asset_id}")
        if row.get("methodology_version") != METHODOLOGY_VERSION:
            raise RuntimeError(f"Crypto current-price methodology mismatch: {universal_asset_id}")
        if row.get("source_table") != SOURCE_TABLE:
            raise RuntimeError(f"Crypto current-price source table mismatch: {universal_asset_id}")
        if row.get("price_semantics") != PRICE_SEMANTICS:
            raise RuntimeError(f"Crypto current-price semantics mismatch: {universal_asset_id}")
        if row.get("presentation_semantics") != PRESENTATION_SEMANTICS:
            raise RuntimeError(f"Crypto current-price presentation semantics mismatch: {universal_asset_id}")
        if not str(row.get("observation_date") or "").strip():
            raise RuntimeError(f"Crypto current-price observation date is missing: {universal_asset_id}")
        if not str(row.get("price_source") or "").strip():
            raise RuntimeError(f"Crypto current-price native source is missing: {universal_asset_id}")
        try:
            price = Decimal(str(row.get("current_price_usd") or ""))
        except Exception as exc:
            raise RuntimeError(f"Crypto current-price value is invalid: {universal_asset_id}") from exc
        if price <= 0:
            raise RuntimeError(f"Crypto current-price value must be positive: {universal_asset_id}")

        seen.add(universal_asset_id)
        records.append(
            PresentationRecord(
                record_type=RECORD_TYPE,
                domain_id=DOMAIN_ID,
                asset_id=universal_asset_id,
                record_key=universal_asset_id,
                payload=dict(row),
            )
        )

    if seen != set(SUPPORTED_ASSETS):
        raise RuntimeError(
            "Crypto current-price certified asset set mismatch: "
            f"observed={sorted(seen)} expected={sorted(SUPPORTED_ASSETS)}"
        )
    records.sort(key=lambda item: item.asset_id or "")
    return records
