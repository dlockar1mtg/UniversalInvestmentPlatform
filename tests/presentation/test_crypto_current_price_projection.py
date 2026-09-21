import csv
import hashlib
import json

import pytest

from foundation.presentation import crypto_current_price_projection as projection
from foundation.production.portfolio_accounting import PortfolioPosition
from foundation.production.portfolio_enrichment import _enrich_position


def certified_delivery(tmp_path, monkeypatch):
    delivery = tmp_path / "uip_delivery" / "pinned"
    delivery.mkdir(parents=True)
    rows = []
    for name, price in (
        ("bitcoin", "86067.0"), ("ethereum", "2764.69"), ("solana", "117.8"),
        ("chainlink", "13.02"), ("xrp", "1.49"), ("avalanche", "11.1"),
    ):
        rows.append({
            "universal_asset_id": f"crypto:{name}", "asset_id": name,
            "observation_date": "2026-09-21", "current_price_usd": price,
            "price_source": "coingecko", "source_priority": "1",
            "collected_at_utc": "2026-09-21 16:59:13.461430+00:00",
            "source_table": projection.SOURCE_TABLE, "authority_id": projection.AUTHORITY,
            "schema_version": "1.0.0", "methodology_version": "1.0.0",
            "price_semantics": projection.PRICE_SEMANTICS,
            "presentation_semantics": projection.PRESENTATION_SEMANTICS,
        })
    csv_path = delivery / "crypto_current_price_v1.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=projection.COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    monkeypatch.setattr(projection, "CSV_SHA256", digest)
    manifest = {
        "status": "CRYPTO_CURRENT_PRICE_V1_PASS", "authority_id": projection.AUTHORITY,
        "schema_version": "1.0.0", "methodology_version": "1.0.0",
        "scope": "SIX_ASSET_LATEST_DAILY_CANONICAL_MARKET_PRICE",
        "source_table": projection.SOURCE_TABLE, "row_count": 6,
        "supported_assets": list(projection.ASSETS),
        "price_semantics": projection.PRICE_SEMANTICS,
        "presentation_semantics": projection.PRESENTATION_SEMANTICS,
        "output_sha256": digest,
        "forecast_input_reused_as_price_authority": False,
        "intraday_quote_claimed": False, "execution_authority_granted": False,
    }
    manifest_path = delivery / "crypto_current_price_v1_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return csv_path, manifest_path


def test_six_prices_project_separately_from_generic_asset(tmp_path, monkeypatch):
    certified_delivery(tmp_path, monkeypatch)
    records = projection.build_crypto_current_price_records(tmp_path)
    assert len(records) == 6
    assert {record.asset_id for record in records} == projection.ASSETS
    assert all(record.record_type == "crypto_current_price" for record in records)


def test_tampering_and_unsafe_manifest_fail_closed(tmp_path, monkeypatch):
    csv_path, manifest_path = certified_delivery(tmp_path, monkeypatch)
    csv_path.write_bytes(csv_path.read_bytes().replace(b"86067.0", b"99999.0"))
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        projection.build_crypto_current_price_records(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    manifest["execution_authority_granted"] = True
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(RuntimeError, match="execution_authority_granted"):
        projection.build_crypto_current_price_records(tmp_path)


def test_portfolio_uses_certified_price_and_preserves_asset_recommendation(tmp_path, monkeypatch):
    certified_delivery(tmp_path, monkeypatch)
    price = next(r.payload for r in projection.build_crypto_current_price_records(tmp_path)
                 if r.asset_id == "crypto:bitcoin")
    # Portfolio enforces the production pin, independently of projection preflight.
    price["_certified_csv_sha256"] = "82416bdc94aa3aa82b1ac8aea8340b3e900609c0a8b3fc876863e1acb0c59315"
    class Reader:
        def asset_detail(self, domain_id, asset_id):
            return {"records": {
                "asset": [{"payload": {"asset_name": "Bitcoin", "asset_symbol": "BTC",
                                       "current_price_usd": None, "current_price_authority_available": False}}],
                "recommendation": [{"payload": {"recommendation": "HOLD"}}],
                "crypto_current_price": [{"payload": price}],
            }}
    from decimal import Decimal
    position = PortfolioPosition("crypto", "crypto:bitcoin", "primary", "USD",
                                 Decimal("0.012355"), "KNOWN", Decimal("0.012355"),
                                 Decimal("0"), Decimal("747.45"), Decimal("60495.45"), Decimal("0"))
    enriched = _enrich_position(position, Reader())
    assert enriched.current_price == Decimal("86067.0")
    assert enriched.recommendation == "HOLD"
    assert enriched.market_value == Decimal("0.012355") * Decimal("86067.0")
