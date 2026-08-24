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

from foundation.presentation.postgres_read_model import PostgresPresentationRepository
from foundation.presentation.publication_model import PresentationPublication, PresentationRecord
from foundation.presentation.publication_service import PresentationPublicationError, publish_presentation_bundle, validate_publication_bundle

CONTRACT_PATH = ROOT / "config" / "presentation" / "metals_price_history_presentation_activation_rehearsal.json"


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
        raise RuntimeError("certified price/history package directory is missing")

    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "METALS-PRICE-HISTORY-PRESENTATION-ACTIVATION-REHEARSAL-1":
        raise RuntimeError("unexpected price/history activation rehearsal contract")
    controls = contract.get("controls") or {}
    if controls.get("presentation_activation_authorized") is not True:
        raise RuntimeError("presentation activation is not authorized")
    for key in (
        "native_source_query_authorized", "export_execution_authorized",
        "production_analytical_database_write_authorized", "forecast_refresh_authorized",
        "model_retraining_authorized", "tactical_posture_authorized",
        "cross_domain_rank_authorized", "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited activation control changed unexpectedly: {key}")

    current_path = package_dir / "metals_current_price.jsonl"
    history_path = package_dir / "metals_price_history.jsonl"
    manifest_path = package_dir / "manifest.json"
    for path in (current_path, history_path, manifest_path):
        if not path.is_file():
            raise RuntimeError(f"required certified package artifact is missing: {path}")

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
        raise RuntimeError("certified price/history package hash mismatch")

    current_rows = load_jsonl(current_path)
    history_rows = load_jsonl(history_path)
    if len(current_rows) != int(contract["expected_current_price_record_count"]):
        raise RuntimeError("current-price package population changed")
    if len(history_rows) != int(contract["expected_history_record_count"]):
        raise RuntimeError("history package population changed")

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
    if str(active_id) != contract["expected_previous_active_publication_id"]:
        raise RuntimeError("unexpected previous active publication")
    if str(active_fingerprint) != contract["expected_previous_fingerprint"]:
        raise RuntimeError("unexpected previous active fingerprint")
    if len(rows) != int(active_count):
        raise RuntimeError("active presentation record population does not reconcile")

    base_records = [
        PresentationRecord(str(record_type), str(domain_id), None if asset_id is None else str(asset_id), str(record_key), dict(payload))
        for record_type, domain_id, asset_id, record_key, payload in rows
    ]
    base = PresentationPublication(
        publication_id="metals-price-history-activation-base",
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
        record.asset_id for record in base_records
        if record.domain_id == "metals" and record.record_type == "asset" and record.asset_id is not None
    }
    governed_asset_ids = {str(row["asset_id"]) for row in current_rows}
    history_asset_ids = {str(row["asset_id"]) for row in history_rows}
    if len(governed_asset_ids) != int(contract["expected_current_price_record_count"]):
        raise RuntimeError("governed current-price asset population changed")
    if history_asset_ids != governed_asset_ids:
        raise RuntimeError("governed price/history package asset coverage differs")
    if not governed_asset_ids.issubset(presentation_metals_asset_ids):
        raise RuntimeError("governed price/history assets are absent from presentation Metals assets")

    current_records: list[PresentationRecord] = []
    for row in current_rows:
        asset_id = str(row["asset_id"])
        payload = dict(row)
        payload["package_id"] = contract["source_package_id"]
        payload["manifest_sha256"] = contract["expected_manifest_sha256"]
        payload["tactical_posture"] = None
        payload["cross_domain_rank"] = None
        payload["automatic_execution_authorized"] = False
        current_records.append(PresentationRecord("metals_current_price", "metals", asset_id, asset_id, payload))

    history_records: list[PresentationRecord] = []
    seen: set[str] = set()
    for row in history_rows:
        asset_id = str(row["asset_id"])
        record_key = f"{asset_id}|{row['observation_date']}"
        if record_key in seen:
            raise RuntimeError(f"duplicate history presentation key: {record_key}")
        seen.add(record_key)
        payload = dict(row)
        payload["package_id"] = contract["source_package_id"]
        payload["manifest_sha256"] = contract["expected_manifest_sha256"]
        history_records.append(PresentationRecord("metals_price_history", "metals", asset_id, record_key, payload))

    extended = PresentationPublication(
        publication_id=str(contract["publication_id"]),
        publication_version=str(version),
        source_database_sha256=str(source_sha),
        source_database_classification=str(source_classification),
        published_at_utc="2026-08-24T18:25:00+00:00",
        publication_status="STAGED",
        records=tuple(sorted(
            tuple(base_records) + tuple(current_records) + tuple(history_records),
            key=lambda item: (item.record_type, item.domain_id, item.asset_id or "", item.record_key),
        )),
    )
    validate_publication_bundle(extended)
    if len(extended.records) != int(contract["expected_extended_record_count"]):
        raise RuntimeError("extended presentation record population changed")
    if extended.content_fingerprint != contract["expected_extended_fingerprint"]:
        raise RuntimeError("extended presentation fingerprint changed")

    store = PostgresPresentationRepository.from_dsn(dsn)
    store.initialize()
    previous = store.active_metadata()
    if not previous:
        raise RuntimeError("no active presentation publication before activation")
    if str(previous["publication_id"]) != contract["expected_previous_active_publication_id"]:
        raise RuntimeError("unexpected active publication before activation")
    if str(previous["content_fingerprint"]) != contract["expected_previous_fingerprint"]:
        raise RuntimeError("unexpected active fingerprint before activation")

    result = publish_presentation_bundle(store, extended)
    if result.status != "ACTIVE":
        raise RuntimeError("price/history presentation did not activate")

    active = store.active_metadata()
    if not active:
        raise RuntimeError("active publication disappeared")
    if str(active["publication_id"]) != str(contract["publication_id"]):
        raise RuntimeError("unexpected active price/history publication")
    if str(active["content_fingerprint"]) != contract["expected_extended_fingerprint"]:
        raise RuntimeError("active price/history fingerprint changed")
    if int(active["record_count"]) != int(contract["expected_extended_record_count"]):
        raise RuntimeError("active price/history record count changed")

    invalid = PresentationPublication(
        publication_id=str(contract["publication_id"]) + "-invalid",
        publication_version=extended.publication_version,
        source_database_sha256=extended.source_database_sha256,
        source_database_classification=extended.source_database_classification,
        published_at_utc=extended.published_at_utc,
        publication_status="STAGED",
        records=tuple(
            item for item in extended.records
            if not (item.record_type == "domain_health" and item.domain_id == "metals")
        ),
    )
    failed = False
    try:
        publish_presentation_bundle(store, invalid)
    except PresentationPublicationError:
        failed = True
    if not failed:
        raise RuntimeError("invalid replacement unexpectedly succeeded")

    active_after = store.active_metadata()
    if not active_after:
        raise RuntimeError("active publication disappeared after invalid replacement")
    if str(active_after["publication_id"]) != str(contract["publication_id"]):
        raise RuntimeError("invalid replacement displaced last-good publication")
    if str(active_after["content_fingerprint"]) != contract["expected_extended_fingerprint"]:
        raise RuntimeError("last-good price/history fingerprint changed")

    payload = {
        "status": "PASS",
        "contract_id": contract["contract_id"],
        "source_package_id": contract["source_package_id"],
        "source_authority": contract["source_authority"],
        "previous_active_publication_id": previous["publication_id"],
        "previous_active_fingerprint": previous["content_fingerprint"],
        "active_publication_id": active_after["publication_id"],
        "active_content_fingerprint": active_after["content_fingerprint"],
        "active_record_count": int(active_after["record_count"]),
        "current_price_record_count": len(current_records),
        "history_record_count": len(history_records),
        "governed_price_history_asset_count": len(governed_asset_ids),
        "invalid_replacement_failed": True,
        "last_good_preserved": True,
        "presentation_activation_executed": True,
        "native_source_query_executed": False,
        "export_execution_executed": False,
        "production_analytical_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": contract["next_decision"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
