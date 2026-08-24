from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.presentation.publication_model import PresentationPublication, PresentationRecord
from foundation.presentation.publication_service import validate_publication_bundle

CONTRACT_PATH = ROOT / "config" / "presentation" / "metals_price_history_presentation_projection_rehearsal.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            text = raw.strip()
            if not text:
                raise RuntimeError(f"blank JSONL row in {path.name} at line {line_number}")
            value = json.loads(text)
            if not isinstance(value, dict):
                raise RuntimeError(f"non-object JSONL row in {path.name} at line {line_number}")
            rows.append(value)
    return rows


def main() -> int:
    args = parse_args()
    package_dir = Path(args.package_dir).resolve()
    if not package_dir.is_dir():
        raise RuntimeError("price/history package directory is missing")

    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "METALS-PRICE-HISTORY-PRESENTATION-PROJECTION-REHEARSAL-1":
        raise RuntimeError("unexpected price/history presentation projection contract")
    controls = contract.get("controls") or {}
    if controls.get("read_only_projection_rehearsal") is not True or controls.get("presentation_projection_authorized") is not True:
        raise RuntimeError("presentation projection rehearsal is not authorized")
    for key in (
        "presentation_activation_authorized",
        "native_source_query_authorized",
        "export_execution_authorized",
        "production_database_write_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "tactical_posture_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
        "missing_authority_may_be_synthesized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited projection control changed unexpectedly: {key}")

    current_path = package_dir / "metals_current_price.jsonl"
    history_path = package_dir / "metals_price_history.jsonl"
    manifest_path = package_dir / "manifest.json"
    for path in (current_path, history_path, manifest_path):
        if not path.is_file():
            raise RuntimeError(f"required package artifact is missing: {path}")

    actual_hashes = {
        "current": sha256_file(current_path),
        "history": sha256_file(history_path),
        "manifest": sha256_file(manifest_path),
    }
    expected_hashes = {
        "current": str(contract["expected_current_price_sha256"]),
        "history": str(contract["expected_price_history_sha256"]),
        "manifest": str(contract["expected_manifest_sha256"]),
    }
    if actual_hashes != expected_hashes:
        raise RuntimeError(f"certified package hash mismatch: {actual_hashes}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("package_id") != contract["source_package_id"]:
        raise RuntimeError("package ID changed")
    if manifest.get("source_authority") != contract["source_authority"]:
        raise RuntimeError("package source authority changed")
    if manifest.get("source_run_id") != contract["source_run_id"]:
        raise RuntimeError("package source run changed")

    current_rows = load_jsonl(current_path)
    history_rows = load_jsonl(history_path)
    if len(current_rows) != int(contract["expected_current_price_record_count"]):
        raise RuntimeError("current-price package population changed")
    if len(history_rows) != int(contract["expected_history_record_count"]):
        raise RuntimeError("history package population changed")

    package_asset_ids = {str(row["asset_id"]) for row in current_rows}
    history_package_asset_ids = {str(row["asset_id"]) for row in history_rows}
    if package_asset_ids != history_package_asset_ids:
        raise RuntimeError("current-price and history package asset coverage differ")
    if len(package_asset_ids) != int(contract["expected_current_price_record_count"]):
        raise RuntimeError("package canonical asset coverage does not reconcile")

    dsn = os.environ.get("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is required")
    import psycopg

    connection = psycopg.connect(dsn)
    try:
        connection.execute("BEGIN READ ONLY")
        metadata = connection.execute(
            """SELECT p.publication_id, p.publication_version, p.source_database_sha256,
                      p.source_database_classification, p.published_at_utc,
                      p.content_fingerprint, p.record_count
               FROM presentation_active_publication a
               JOIN presentation_publications p USING (publication_id)
               WHERE a.singleton_id=1"""
        ).fetchone()
        if metadata is None:
            raise RuntimeError("no active presentation publication")
        rows = connection.execute(
            """SELECT r.record_type, r.domain_id, r.asset_id, r.record_key, r.payload_json
               FROM presentation_records r
               JOIN presentation_active_publication a ON a.publication_id=r.publication_id
               WHERE a.singleton_id=1
               ORDER BY r.record_type, r.domain_id, COALESCE(r.asset_id,''), r.record_key"""
        ).fetchall()
        connection.rollback()
    finally:
        connection.close()

    active_id, version, source_sha, source_classification, published_at, active_fingerprint, active_count = metadata
    if str(active_id) != contract["expected_active_publication_id"]:
        raise RuntimeError("unexpected active presentation publication")
    if str(active_fingerprint) != contract["expected_active_fingerprint"]:
        raise RuntimeError("unexpected active presentation fingerprint")
    if int(active_count) != int(contract["expected_base_record_count"]):
        raise RuntimeError("active presentation record count changed")
    if len(rows) != int(active_count):
        raise RuntimeError("active presentation stored record population does not reconcile")

    base_records = [
        PresentationRecord(str(record_type), str(domain_id), None if asset_id is None else str(asset_id), str(record_key), dict(payload))
        for record_type, domain_id, asset_id, record_key, payload in rows
    ]
    base = PresentationPublication(
        publication_id="metals-price-history-projection-rehearsal-base",
        publication_version=str(version),
        source_database_sha256=str(source_sha),
        source_database_classification=str(source_classification),
        published_at_utc=str(published_at),
        publication_status="STAGED",
        records=tuple(base_records),
    )
    validate_publication_bundle(base)
    if base.content_fingerprint != str(active_fingerprint):
        raise RuntimeError("reconstructed active presentation fingerprint mismatch")

    presentation_metals_asset_ids = {
        str(record.asset_id)
        for record in base_records
        if record.domain_id == "metals" and record.record_type == "asset" and record.asset_id is not None
    }
    missing_package_assets = sorted(package_asset_ids - presentation_metals_asset_ids)
    if missing_package_assets:
        raise RuntimeError(f"price/history package references absent presentation assets: {missing_package_assets}")

    current_records: list[PresentationRecord] = []
    for row in current_rows:
        asset_id = str(row["asset_id"])
        payload = dict(row)
        payload["package_id"] = contract["source_package_id"]
        payload["manifest_sha256"] = contract["expected_manifest_sha256"]
        payload["tactical_posture"] = None
        payload["cross_domain_rank"] = None
        payload["automatic_execution_authorized"] = False
        current_records.append(PresentationRecord(
            str(contract["current_price_record_type"]), "metals", asset_id, asset_id, payload
        ))

    history_records: list[PresentationRecord] = []
    seen_history_keys: set[str] = set()
    for row in history_rows:
        asset_id = str(row["asset_id"])
        record_key = f"{asset_id}|{row['observation_date']}"
        if record_key in seen_history_keys:
            raise RuntimeError(f"duplicate history presentation key: {record_key}")
        seen_history_keys.add(record_key)
        payload = dict(row)
        payload["package_id"] = contract["source_package_id"]
        payload["manifest_sha256"] = contract["expected_manifest_sha256"]
        history_records.append(PresentationRecord(
            str(contract["price_history_record_type"]), "metals", asset_id, record_key, payload
        ))

    all_records = tuple(sorted(
        tuple(base_records) + tuple(current_records) + tuple(history_records),
        key=lambda item: (item.record_type, item.domain_id, item.asset_id or "", item.record_key),
    ))
    extended = PresentationPublication(
        publication_id="dash-read-1-metals-price-history-projection-rehearsal",
        publication_version=str(version),
        source_database_sha256=str(source_sha),
        source_database_classification=str(source_classification),
        published_at_utc="2026-08-24T18:15:00+00:00",
        publication_status="STAGED",
        records=all_records,
    )
    validate_publication_bundle(extended)
    if len(extended.records) != int(contract["expected_extended_record_count"]):
        raise RuntimeError("extended price/history presentation count does not reconcile")

    current_asset_ids = {str(record.asset_id) for record in current_records if record.asset_id is not None}
    history_asset_ids = {str(record.asset_id) for record in history_records if record.asset_id is not None}
    if current_asset_ids != package_asset_ids or history_asset_ids != package_asset_ids:
        raise RuntimeError("price/history presentation governed-vehicle coverage does not reconcile")

    coverage = []
    for asset_id in sorted(package_asset_ids):
        history_count = sum(1 for item in history_records if item.asset_id == asset_id)
        current = next(item for item in current_records if item.asset_id == asset_id)
        coverage.append({
            "asset_id": asset_id,
            "current_price_usd": current.payload["current_price_usd"],
            "observation_date": current.payload["observation_date"],
            "history_count": history_count,
        })

    result = {
        "status": "PASS",
        "read_only": True,
        "contract_id": contract["contract_id"],
        "source_package_id": contract["source_package_id"],
        "source_authority": contract["source_authority"],
        "base_publication_id": str(active_id),
        "base_content_fingerprint": str(active_fingerprint),
        "base_record_count": len(base_records),
        "presentation_metals_asset_count": len(presentation_metals_asset_ids),
        "governed_price_history_asset_count": len(package_asset_ids),
        "current_price_record_count": len(current_records),
        "history_record_count": len(history_records),
        "extended_record_count": len(extended.records),
        "extended_content_fingerprint": extended.content_fingerprint,
        "current_price_record_type": contract["current_price_record_type"],
        "price_history_record_type": contract["price_history_record_type"],
        "coverage": coverage,
        "active_publication_unchanged": True,
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
