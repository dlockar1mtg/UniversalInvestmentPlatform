"""Fail-closed projection of the pinned Crypto Current Price V1 authority."""
from __future__ import annotations

import csv
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from foundation.presentation.publication_model import PresentationRecord

RECORD_TYPE = "crypto_current_price"
AUTHORITY = "CRYPTO_CANONICAL_MARKET_DAILY_CURRENT_PRICE_V1"
CSV_SHA256 = "82416bdc94aa3aa82b1ac8aea8340b3e900609c0a8b3fc876863e1acb0c59315"
ASSETS = frozenset(f"crypto:{asset}" for asset in (
    "bitcoin", "ethereum", "solana", "chainlink", "xrp", "avalanche"
))
PRICE_SEMANTICS = "DAILY_CANONICAL_MARKET_CLOSE"
PRESENTATION_SEMANTICS = "CURRENT_PRICE_FOR_PORTFOLIO_VALUATION_NOT_EXECUTION_QUOTE"
SOURCE_TABLE = "canonical_market_daily"
COLUMNS = (
    "universal_asset_id", "asset_id", "observation_date", "current_price_usd",
    "price_source", "source_priority", "collected_at_utc", "source_table",
    "authority_id", "schema_version", "methodology_version", "price_semantics",
    "presentation_semantics",
)


def build_crypto_current_price_records(artifact_root: Path) -> list[PresentationRecord]:
    deliveries = list(artifact_root.glob("uip_delivery/*/crypto_current_price_v1_manifest.json"))
    if len(deliveries) != 1:
        raise RuntimeError(f"Expected one Crypto Current Price V1 delivery, got {len(deliveries)}")
    manifest_path = deliveries[0]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {
        "status": "CRYPTO_CURRENT_PRICE_V1_PASS",
        "authority_id": AUTHORITY,
        "schema_version": "1.0.0",
        "methodology_version": "1.0.0",
        "scope": "SIX_ASSET_LATEST_DAILY_CANONICAL_MARKET_PRICE",
        "source_table": SOURCE_TABLE,
        "row_count": 6,
        "price_semantics": PRICE_SEMANTICS,
        "presentation_semantics": PRESENTATION_SEMANTICS,
        "output_sha256": CSV_SHA256,
        "forecast_input_reused_as_price_authority": False,
        "intraday_quote_claimed": False,
        "execution_authority_granted": False,
    }
    for key, value in expected.items():
        if type(manifest.get(key)) is not type(value) or manifest[key] != value:
            raise RuntimeError(f"Crypto Current Price V1 manifest mismatch: {key}")
    if set(manifest.get("supported_assets", [])) != ASSETS or len(manifest["supported_assets"]) != 6:
        raise RuntimeError("Crypto Current Price V1 supported asset set mismatch")

    csv_path = manifest_path.with_name("crypto_current_price_v1.csv")
    raw = csv_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CSV_SHA256:
        raise RuntimeError("Crypto Current Price V1 CSV SHA-256 mismatch")
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise RuntimeError("Crypto Current Price V1 CSV schema mismatch")
        rows = list(reader)
    if len(rows) != 6:
        raise RuntimeError("Crypto Current Price V1 row count mismatch")
    records = []
    seen = set()
    for row in rows:
        identity = row["universal_asset_id"]
        if identity not in ASSETS or identity in seen or row["asset_id"] != identity.removeprefix("crypto:"):
            raise RuntimeError("Crypto Current Price V1 row identity mismatch")
        seen.add(identity)
        fields = {
            "authority_id": AUTHORITY,
            "source_table": SOURCE_TABLE,
            "schema_version": "1.0.0",
            "methodology_version": "1.0.0",
            "price_semantics": PRICE_SEMANTICS,
            "presentation_semantics": PRESENTATION_SEMANTICS,
            "price_source": "coingecko",
            "source_priority": "1",
            "observation_date": "2026-09-21",
        }
        if any(row[key] != value for key, value in fields.items()) or not row["collected_at_utc"]:
            raise RuntimeError(f"Crypto Current Price V1 row authority mismatch: {identity}")
        try:
            price = Decimal(row["current_price_usd"])
        except InvalidOperation as exc:
            raise RuntimeError(f"Invalid Crypto price: {identity}") from exc
        if not price.is_finite() or price <= 0:
            raise RuntimeError(f"Invalid Crypto price: {identity}")
        records.append(PresentationRecord(
            record_type=RECORD_TYPE, domain_id="crypto", asset_id=identity,
            record_key=identity,
            payload={**row, "_certified_csv_sha256": CSV_SHA256,
                     "_certified_manifest_status": manifest["status"]},
        ))
    if seen != ASSETS:
        raise RuntimeError("Crypto Current Price V1 missing canonical identities")
    return records
