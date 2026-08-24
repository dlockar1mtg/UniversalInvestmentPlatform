from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.presentation.postgres_read_model import PostgresPresentationRepository
from foundation.presentation.publication_model import PresentationPublication, build_presentation_publication
from foundation.presentation.publication_service import PresentationPublicationError, publish_presentation_bundle, validate_publication_bundle
from scripts.rehearse_metals_momentum_presentation_contract_extension import _load_contract, _momentum_records

ACTIVATION_CONTRACT_PATH = ROOT / "config" / "presentation" / "dash_read_1_metals_momentum_activation_rehearsal.json"
EXPECTED_SOURCE_SHA256 = "dff98e56d27cbc5ef879c18939309c5ab8661fa8fa6dfe74e82537fd53954f7c"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--expected-sha256", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database = Path(args.database).resolve()
    expected_sha = args.expected_sha256.strip().lower()
    if expected_sha != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("unexpected analytical DuckDB SHA-256 authority")
    if not database.is_file():
        raise RuntimeError("analytical DuckDB is missing")

    dsn = os.environ.get("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is required")

    activation = json.loads(ACTIVATION_CONTRACT_PATH.read_text(encoding="utf-8"))
    if activation.get("contract_id") != "DASH-READ-1-METALS-MOMENTUM-ACTIVATION-REHEARSAL-1":
        raise RuntimeError("unexpected activation rehearsal contract")
    controls = activation.get("controls") or {}
    if controls.get("presentation_activation_authorized") is not True:
        raise RuntimeError("presentation activation is not authorized")
    for key in (
        "production_analytical_database_write_authorized", "forecast_refresh_authorized",
        "model_retraining_authorized", "tactical_posture_authorized",
        "cross_domain_rank_authorized", "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited activation control changed unexpectedly: {key}")

    extension = _load_contract()
    duck = duckdb.connect(str(database), read_only=True)
    try:
        base = build_presentation_publication(
            ROOT,
            database,
            duck,
            publication_id=str(activation["publication_id"]),
            published_at_utc="2026-08-24T17:40:00+00:00",
        )
    finally:
        duck.close()
    validate_publication_bundle(base)

    momentum = _momentum_records(dsn, extension)
    extended = replace(
        base,
        records=tuple(sorted(
            tuple(base.records) + tuple(momentum),
            key=lambda item: (item.record_type, item.domain_id, item.asset_id or "", item.record_key),
        )),
    )
    validate_publication_bundle(extended)

    if len(extended.records) != int(activation["expected_extended_record_count"]):
        raise RuntimeError("extended presentation record population changed")
    if extended.content_fingerprint != activation["expected_extended_fingerprint"]:
        raise RuntimeError("extended presentation fingerprint changed")

    store = PostgresPresentationRepository.from_dsn(dsn)
    store.initialize()
    previous = store.active_metadata()
    if not previous:
        raise RuntimeError("no active presentation publication")
    if str(previous["publication_id"]) != activation["expected_previous_active_publication_id"]:
        raise RuntimeError("unexpected previous active publication")
    if str(previous["content_fingerprint"]) != activation["expected_previous_fingerprint"]:
        raise RuntimeError("unexpected previous active fingerprint")

    result = publish_presentation_bundle(store, extended)
    if result.status != "ACTIVE":
        raise RuntimeError("momentum presentation publication did not activate")

    active = store.active_metadata()
    if not active:
        raise RuntimeError("active publication disappeared")
    if str(active["publication_id"]) != str(activation["publication_id"]):
        raise RuntimeError("unexpected active momentum publication")
    if str(active["content_fingerprint"]) != activation["expected_extended_fingerprint"]:
        raise RuntimeError("active momentum fingerprint changed")
    if int(active["record_count"]) != int(activation["expected_extended_record_count"]):
        raise RuntimeError("active momentum record count changed")

    invalid = PresentationPublication(
        publication_id=str(activation["publication_id"]) + "-invalid",
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
    if str(active_after["publication_id"]) != str(activation["publication_id"]):
        raise RuntimeError("invalid replacement displaced last-good publication")
    if str(active_after["content_fingerprint"]) != activation["expected_extended_fingerprint"]:
        raise RuntimeError("last-good fingerprint changed after invalid replacement")

    payload = {
        "status": "PASS",
        "contract_id": activation["contract_id"],
        "previous_active_publication_id": previous["publication_id"],
        "previous_active_fingerprint": previous["content_fingerprint"],
        "active_publication_id": active_after["publication_id"],
        "active_content_fingerprint": active_after["content_fingerprint"],
        "active_record_count": int(active_after["record_count"]),
        "momentum_record_count": len(momentum),
        "invalid_replacement_failed": True,
        "last_good_preserved": True,
        "presentation_activation_executed": True,
        "production_analytical_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": activation["next_decision"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
