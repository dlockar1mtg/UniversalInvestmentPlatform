from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.presentation.read_api import PresentationReadRepository

CONTRACT_PATH = ROOT / "config" / "presentation" / "metals_price_history_read_api_verification.json"


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "METALS-PRICE-HISTORY-READ-API-VERIFY-1":
        raise RuntimeError("unexpected price/history read API verification contract")
    controls = contract.get("controls") or {}
    if controls.get("read_only_verification") is not True:
        raise RuntimeError("read-only verification is not authorized")
    for key in (
        "native_source_query_authorized",
        "export_execution_authorized",
        "production_database_write_authorized",
        "presentation_activation_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "tactical_posture_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
        "missing_authority_may_be_synthesized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited verification control changed unexpectedly: {key}")

    dsn = os.environ.get("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is required")

    repository = PresentationReadRepository.from_dsn(dsn)
    metadata = repository.active_metadata()
    if metadata is None:
        raise RuntimeError("no active presentation publication")
    if str(metadata["publication_id"]) != contract["expected_active_publication_id"]:
        raise RuntimeError("unexpected active price/history publication")
    if str(metadata["content_fingerprint"]) != contract["expected_active_fingerprint"]:
        raise RuntimeError("unexpected active price/history fingerprint")
    if int(metadata["record_count"]) != int(contract["expected_active_record_count"]):
        raise RuntimeError("unexpected active price/history record count")

    import psycopg

    connection = psycopg.connect(dsn)
    try:
        connection.execute("BEGIN READ ONLY")
        metals_asset_rows = connection.execute(
            """SELECT asset_id
               FROM presentation_records
               WHERE publication_id=%s AND domain_id='metals' AND record_type='asset'
               ORDER BY asset_id""",
            (contract["expected_active_publication_id"],),
        ).fetchall()
        current_count = int(connection.execute(
            """SELECT COUNT(*)
               FROM presentation_records
               WHERE publication_id=%s AND domain_id='metals' AND record_type=%s""",
            (contract["expected_active_publication_id"], contract["current_price_record_type"]),
        ).fetchone()[0])
        history_count = int(connection.execute(
            """SELECT COUNT(*)
               FROM presentation_records
               WHERE publication_id=%s AND domain_id='metals' AND record_type=%s""",
            (contract["expected_active_publication_id"], contract["price_history_record_type"]),
        ).fetchone()[0])
        connection.rollback()
    finally:
        connection.close()

    metals_asset_ids = [str(row[0]) for row in metals_asset_rows]
    governed = [str(value) for value in contract["governed_asset_ids"]]
    governed_set = set(governed)
    metals_set = set(metals_asset_ids)
    if len(metals_asset_ids) != int(contract["expected_metals_asset_count"]):
        raise RuntimeError("Metals presentation asset count changed")
    if not governed_set.issubset(metals_set):
        raise RuntimeError("governed price/history assets are not a subset of Metals presentation assets")
    if current_count != int(contract["expected_current_price_record_count"]):
        raise RuntimeError("live current-price record population changed")
    if history_count != int(contract["expected_history_record_count"]):
        raise RuntimeError("live price-history record population changed")

    details = []
    for asset_id in sorted(governed):
        detail = repository.asset_detail("metals", asset_id)
        if detail is None:
            raise RuntimeError(f"governed asset missing from read API: {asset_id}")
        records = detail["records"]
        required = (
            "asset",
            contract["momentum_record_type"],
            contract["current_price_record_type"],
            contract["price_history_record_type"],
        )
        for record_type in required:
            if record_type not in records:
                raise RuntimeError(f"{record_type} missing from read API for {asset_id}")
        current_rows = list(records[contract["current_price_record_type"]])
        history_rows = list(records[contract["price_history_record_type"]])
        if len(current_rows) != 1:
            raise RuntimeError(f"expected exactly one current-price row for {asset_id}")
        if len(history_rows) != int(contract["expected_history_points_per_governed_asset"]):
            raise RuntimeError(f"unexpected history population for {asset_id}: {len(history_rows)}")
        current_payload = current_rows[0]["payload"]
        if current_payload.get("source_authority") != contract["source_authority"]:
            raise RuntimeError(f"current-price source authority changed for {asset_id}")
        if current_payload.get("package_id") != contract["source_package_id"]:
            raise RuntimeError(f"current-price package lineage changed for {asset_id}")
        if float(current_payload.get("current_price_usd") or 0) <= 0:
            raise RuntimeError(f"invalid live current price for {asset_id}")
        latest_history = history_rows[-1]["payload"]
        if str(latest_history.get("observation_date")) != str(current_payload.get("observation_date")):
            raise RuntimeError(f"current-price/latest-history date mismatch for {asset_id}")
        effective_latest = latest_history.get("adjusted_close_usd")
        if effective_latest is None:
            effective_latest = latest_history.get("close_usd")
        if float(effective_latest) != float(current_payload["current_price_usd"]):
            raise RuntimeError(f"current-price/latest-history value mismatch for {asset_id}")
        if current_payload.get("tactical_posture") is not None:
            raise RuntimeError(f"tactical posture unexpectedly populated for {asset_id}")
        if current_payload.get("cross_domain_rank") is not None:
            raise RuntimeError(f"cross-domain rank unexpectedly populated for {asset_id}")
        if current_payload.get("automatic_execution_authorized") is not False:
            raise RuntimeError(f"automatic execution unexpectedly authorized for {asset_id}")
        details.append({
            "asset_id": asset_id,
            "record_types": sorted(records.keys()),
            "current_price_usd": current_payload["current_price_usd"],
            "observation_date": current_payload["observation_date"],
            "history_count": len(history_rows),
        })

    ungoverned = sorted(metals_set - governed_set)
    if len(ungoverned) != int(contract["expected_metals_asset_count"]) - int(contract["expected_governed_asset_count"]):
        raise RuntimeError("ungoverned Metals asset population does not reconcile")
    ungoverned_details = []
    for asset_id in ungoverned:
        detail = repository.asset_detail("metals", asset_id)
        if detail is None:
            raise RuntimeError(f"ungoverned Metals asset disappeared from read API: {asset_id}")
        record_types = sorted(detail["records"].keys())
        if contract["current_price_record_type"] in record_types:
            raise RuntimeError(f"ungoverned asset received fabricated current-price authority: {asset_id}")
        if contract["price_history_record_type"] in record_types:
            raise RuntimeError(f"ungoverned asset received fabricated price-history authority: {asset_id}")
        ungoverned_details.append({"asset_id": asset_id, "record_types": record_types})

    result = {
        "status": "PASS",
        "read_only": True,
        "contract_id": contract["contract_id"],
        "active_publication_id": metadata["publication_id"],
        "active_content_fingerprint": metadata["content_fingerprint"],
        "active_record_count": int(metadata["record_count"]),
        "source_package_id": contract["source_package_id"],
        "source_authority": contract["source_authority"],
        "presentation_metals_asset_count": len(metals_asset_ids),
        "governed_price_history_asset_count": len(governed),
        "ungoverned_metals_asset_count": len(ungoverned),
        "current_price_record_count": current_count,
        "history_record_count": history_count,
        "asset_details": details,
        "ungoverned_asset_details": ungoverned_details,
        "price_history_read_api_verified": True,
        "missing_authority_preserved": True,
        "native_source_query_executed": False,
        "export_execution_executed": False,
        "production_database_write_executed": False,
        "presentation_activation_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": contract["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
