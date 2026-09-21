from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from foundation.presentation.crypto_current_price_projection import (
    AUTHORITY_ID,
    PRICE_SEMANTICS,
    PRESENTATION_SEMANTICS,
    RECORD_TYPE,
    SUPPORTED_ASSETS,
    build_crypto_current_price_records,
)


def _write_artifact(root: Path) -> None:
    delivery = root / "uip_delivery" / "gha-test"
    delivery.mkdir(parents=True)
    csv_path = delivery / "crypto_current_price_v1.csv"
    fieldnames = (
        "universal_asset_id",
        "asset_id",
        "observation_date",
        "current_price_usd",
        "price_source",
        "source_priority",
        "collected_at_utc",
        "source_table",
        "authority_id",
        "schema_version",
        "methodology_version",
        "price_semantics",
        "presentation_semantics",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, universal_asset_id in enumerate(SUPPORTED_ASSETS, start=1):
            native = universal_asset_id.split(":", 1)[1]
            writer.writerow({
                "universal_asset_id": universal_asset_id,
                "asset_id": native,
                "observation_date": "2026-09-21",
                "current_price_usd": str(index * 100),
                "price_source": "coingecko",
                "source_priority": "1",
                "collected_at_utc": "2026-09-21 16:59:13+00:00",
                "source_table": "canonical_market_daily",
                "authority_id": AUTHORITY_ID,
                "schema_version": "1.0.0",
                "methodology_version": "1.0.0",
                "price_semantics": PRICE_SEMANTICS,
                "presentation_semantics": PRESENTATION_SEMANTICS,
            })
    sha = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    manifest = {
        "status": "CRYPTO_CURRENT_PRICE_V1_PASS",
        "authority_id": AUTHORITY_ID,
        "schema_version": "1.0.0",
        "methodology_version": "1.0.0",
        "scope": "SIX_ASSET_LATEST_DAILY_CANONICAL_MARKET_PRICE",
        "source_table": "canonical_market_daily",
        "row_count": 6,
        "supported_assets": list(SUPPORTED_ASSETS),
        "price_semantics": PRICE_SEMANTICS,
        "presentation_semantics": PRESENTATION_SEMANTICS,
        "output_sha256": sha,
        "forecast_input_reused_as_price_authority": False,
        "intraday_quote_claimed": False,
        "execution_authority_granted": False,
    }
    (delivery / "crypto_current_price_v1_manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )


def test_projection_emits_exact_six_certified_crypto_current_price_records(tmp_path: Path):
    _write_artifact(tmp_path)
    records = build_crypto_current_price_records(tmp_path)
    assert len(records) == 6
    assert {record.asset_id for record in records} == set(SUPPORTED_ASSETS)
    assert all(record.domain_id == "crypto" for record in records)
    assert all(record.record_type == RECORD_TYPE for record in records)
    bitcoin = next(record for record in records if record.asset_id == "crypto:bitcoin")
    assert bitcoin.payload["authority_id"] == AUTHORITY_ID
    assert bitcoin.payload["source_table"] == "canonical_market_daily"
    assert bitcoin.payload["price_semantics"] == PRICE_SEMANTICS
    assert bitcoin.payload["presentation_semantics"] == PRESENTATION_SEMANTICS


def test_projection_rejects_manifest_sha_drift(tmp_path: Path):
    _write_artifact(tmp_path)
    csv_path = next(tmp_path.rglob("crypto_current_price_v1.csv"))
    csv_path.write_text(csv_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="SHA-256"):
        build_crypto_current_price_records(tmp_path)


def test_projection_rejects_duplicate_or_missing_authority_files(tmp_path: Path):
    _write_artifact(tmp_path)
    duplicate = tmp_path / "duplicate"
    duplicate.mkdir()
    source = next(tmp_path.rglob("crypto_current_price_v1.csv"))
    (duplicate / source.name).write_bytes(source.read_bytes())
    with pytest.raises(RuntimeError, match="exactly one"):
        build_crypto_current_price_records(tmp_path)
