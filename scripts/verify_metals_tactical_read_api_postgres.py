from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.presentation.read_api import PresentationReadRepository

EXPECTED_PUBLICATION_ID = "dash-read-1-metals-tactical-dff98e56d27c"
EXPECTED_SOURCE_SHA256 = "dff98e56d27cbc5ef879c18939309c5ab8661fa8fa6dfe74e82537fd53954f7c"
EXPECTED_FINGERPRINT = "fa76508d2c009a644eba9eabaef3600eb96459441336577a16c5f97299f9dda0"
EXPECTED_RECORD_COUNT = 4171


def _record_counts(detail: dict[str, object]) -> dict[str, int]:
    records = detail.get("records") or {}
    return {str(key): len(value) for key, value in records.items()}


def _find_asset_id(catalog: tuple[dict[str, object], ...], *, symbol: str | None = None, name: str | None = None) -> str:
    matches = []
    for item in catalog:
        item_symbol = item.get("asset_symbol")
        item_name = item.get("asset_name")
        if symbol is not None and str(item_symbol or "").upper() == symbol.upper():
            matches.append(item)
        elif name is not None and str(item_name or "").strip().lower() == name.strip().lower():
            matches.append(item)
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one catalog match for symbol={symbol!r} name={name!r}; got {len(matches)}")
    asset_id = matches[0].get("asset_id")
    if not asset_id:
        raise RuntimeError("Matched catalog item has no asset_id.")
    return str(asset_id)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the active Metals tactical presentation through PresentationReadRepository.")
    parser.parse_args()

    dsn = os.getenv("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is not available in this process.")

    repository = PresentationReadRepository.from_dsn(dsn)
    if not repository.readiness():
        raise RuntimeError("PresentationReadRepository is not ready.")

    metadata = repository.active_metadata()
    if metadata is None:
        raise RuntimeError("No active presentation publication.")

    if str(metadata.get("publication_id")) != EXPECTED_PUBLICATION_ID:
        raise RuntimeError(f"Unexpected active publication ID: {metadata.get('publication_id')}")
    if str(metadata.get("source_database_sha256")) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("Active presentation source SHA-256 changed.")
    if str(metadata.get("content_fingerprint")) != EXPECTED_FINGERPRINT:
        raise RuntimeError("Active presentation fingerprint changed.")
    if int(metadata.get("record_count") or -1) != EXPECTED_RECORD_COUNT:
        raise RuntimeError("Active presentation record count changed.")
    if str(metadata.get("publication_status")) != "ACTIVE":
        raise RuntimeError("Active presentation metadata is not ACTIVE.")

    catalog = repository.recommendation_catalog(domain_id="metals", limit=200, offset=0)
    if len(catalog) != 12:
        raise RuntimeError(f"Unexpected Metals recommendation catalog size: {len(catalog)}")

    gold_id = _find_asset_id(catalog, name="Gold")
    gld_id = _find_asset_id(catalog, symbol="GLD")

    gold = repository.asset_detail("metals", gold_id)
    gld = repository.asset_detail("metals", gld_id)
    if gold is None or gld is None:
        raise RuntimeError("Gold or GLD detail is unavailable through the read repository.")

    gold_counts = _record_counts(gold)
    gld_counts = _record_counts(gld)

    expected_gold = {
        "asset": 1,
        "forecast": 4,
        "metals_model_component": 16,
        "metals_regime_probability": 3,
        "recommendation": 1,
    }
    expected_gld = {
        "asset": 1,
        "metals_recommendation_change": 1,
        "metals_uncertainty_adjusted": 4,
        "recommendation": 1,
        "risk": 1,
    }
    if gold_counts != expected_gold:
        raise RuntimeError(f"Unexpected Gold read API record counts: {gold_counts}")
    if gld_counts != expected_gld:
        raise RuntimeError(f"Unexpected GLD read API record counts: {gld_counts}")

    gold_lineage = repository.lineage("metals", gold_id)
    gld_lineage = repository.lineage("metals", gld_id)
    if not gold_lineage or not gold_lineage.get("items"):
        raise RuntimeError("Gold lineage is missing from read API repository.")
    if not gld_lineage or not gld_lineage.get("items"):
        raise RuntimeError("GLD lineage is missing from read API repository.")

    payload = {
        "status": "PASS",
        "read_only": True,
        "active_publication_id": EXPECTED_PUBLICATION_ID,
        "source_database_sha256": EXPECTED_SOURCE_SHA256,
        "content_fingerprint": EXPECTED_FINGERPRINT,
        "record_count": EXPECTED_RECORD_COUNT,
        "metals_recommendation_catalog_count": len(catalog),
        "gold_asset_id": gold_id,
        "gold_record_counts": gold_counts,
        "gld_asset_id": gld_id,
        "gld_record_counts": gld_counts,
        "gold_lineage_items": len(gold_lineage["items"]),
        "gld_lineage_items": len(gld_lineage["items"]),
        "cross_domain_rank_authorized": False,
        "tactical_posture_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": "AUTHORIZE_METALS_MARKET_HISTORY_AUTHORITY_AUDIT",
    }
    print(json.dumps(payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
