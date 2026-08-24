"""Rehearse and activate the verified Metals tactical presentation projection in PostgreSQL/Neon."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import duckdb
import psycopg

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.presentation.postgres_read_model import PostgresPresentationRepository
from foundation.presentation.publication_model import PresentationPublication, build_presentation_publication
from foundation.presentation.publication_service import (
    PresentationPublicationError,
    publish_presentation_bundle,
    validate_publication_bundle,
)

EXPECTED_TOTAL_RECORDS = 4171
EXPECTED_FINGERPRINT = "fa76508d2c009a644eba9eabaef3600eb96459441336577a16c5f97299f9dda0"
EXPECTED_COUNTS = [
    ("crypto", "asset", 6),
    ("crypto", "domain_health", 1),
    ("crypto", "forecast", 120),
    ("crypto", "recommendation", 6),
    ("crypto", "risk", 6),
    ("metals", "asset", 16),
    ("metals", "domain_health", 1),
    ("metals", "forecast", 16),
    ("metals", "metals_data_freshness", 21),
    ("metals", "metals_model_component", 64),
    ("metals", "metals_platform_health", 1),
    ("metals", "metals_recommendation_change", 10),
    ("metals", "metals_regime_probability", 12),
    ("metals", "metals_uncertainty_adjusted", 32),
    ("metals", "recommendation", 12),
    ("metals", "risk", 11),
    ("mtg", "asset", 968),
    ("mtg", "domain_health", 1),
    ("mtg", "forecast", 931),
    ("mtg", "native_authority", 968),
    ("mtg", "recommendation", 968),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--expected-sha256", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database = Path(args.database).resolve()
    expected_sha = args.expected_sha256.strip().lower()
    dsn = os.getenv("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is not available in this process.")

    print("=" * 100)
    print("UIP METALS TACTICAL PRESENTATION - POSTGRESQL REPUBLICATION REHEARSAL")
    print("=" * 100)
    print("UIIP_DATABASE_URL_PRESENT=TRUE")
    print("UIIP_DATABASE_URL_VALUE=REDACTED")

    with psycopg.connect(dsn) as pg, pg.cursor() as cursor:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
        tables_before = [row[0] for row in cursor.fetchall()]
    existing_non_presentation = {name for name in tables_before if not name.startswith("presentation_")}
    print(f"POSTGRES_TABLE_COUNT_BEFORE={len(tables_before)}")
    print(f"NON_PRESENTATION_TABLE_COUNT_BEFORE={len(existing_non_presentation)}")

    store = PostgresPresentationRepository.from_dsn(dsn)
    store.initialize()
    print("PRESENTATION_SCHEMA_INITIALIZATION=PASS")

    with psycopg.connect(dsn) as pg, pg.cursor() as cursor:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'presentation_%' ORDER BY table_name")
        presentation_tables = [row[0] for row in cursor.fetchall()]
    expected_tables = ["presentation_active_publication", "presentation_publications", "presentation_records"]
    if presentation_tables != expected_tables:
        raise RuntimeError(f"Unexpected PostgreSQL presentation table set: {presentation_tables}")
    print(f"PRESENTATION_TABLES={presentation_tables!r}")

    duck = duckdb.connect(str(database), read_only=True)
    try:
        publication = build_presentation_publication(
            ROOT,
            database,
            duck,
            publication_id=f"dash-read-1-metals-tactical-{expected_sha[:12]}",
            published_at_utc="2026-08-24T12:00:00+00:00",
        )
    finally:
        duck.close()

    validate_publication_bundle(publication)
    print(f"CERTIFIED_PUBLICATION_ID={publication.publication_id}")
    print(f"CERTIFIED_PUBLICATION_RECORD_COUNT={len(publication.records)}")
    print(f"CERTIFIED_PUBLICATION_FINGERPRINT={publication.content_fingerprint}")
    if publication.source_database_sha256 != expected_sha:
        raise RuntimeError("Publication source SHA changed.")
    if len(publication.records) != EXPECTED_TOTAL_RECORDS:
        raise RuntimeError(f"Unexpected presentation record count: {len(publication.records)}")
    if publication.content_fingerprint != EXPECTED_FINGERPRINT:
        raise RuntimeError("Verified presentation content fingerprint changed.")

    previous = store.active_metadata()
    previous_id = None if not previous else str(previous["publication_id"])
    previous_fingerprint = None if not previous else str(previous["content_fingerprint"])
    print(f"PREVIOUS_ACTIVE_PUBLICATION={previous_id!r}")

    result = publish_presentation_bundle(store, publication)
    if result.status != "ACTIVE":
        raise RuntimeError("Metals tactical publication did not activate.")

    active = store.active_metadata()
    if not active:
        raise RuntimeError("PostgreSQL has no active presentation publication.")
    if active["publication_id"] != publication.publication_id:
        raise RuntimeError("Unexpected active publication ID.")
    if active["source_database_sha256"] != expected_sha:
        raise RuntimeError("Active publication source SHA changed.")
    if int(active["record_count"]) != EXPECTED_TOTAL_RECORDS:
        raise RuntimeError("Active presentation record count changed.")
    if str(active["content_fingerprint"]) != EXPECTED_FINGERPRINT:
        raise RuntimeError("Active presentation fingerprint changed.")
    active_id = str(active["publication_id"])
    active_fingerprint = str(active["content_fingerprint"])
    print(f"ACTIVE_PUBLICATION_METADATA={active!r}")
    print("METALS_TACTICAL_POSTGRES_ACTIVATION=PASS")

    with psycopg.connect(dsn) as pg, pg.cursor() as cursor:
        cursor.execute(
            """SELECT domain_id, record_type, COUNT(*) FROM presentation_records
               WHERE publication_id=%s GROUP BY domain_id, record_type ORDER BY domain_id, record_type""",
            (publication.publication_id,),
        )
        counts = [(str(d), str(t), int(c)) for d, t, c in cursor.fetchall()]
        cursor.execute(
            """SELECT record_type, COUNT(*) FROM presentation_records
               WHERE publication_id=%s AND domain_id='metals'
                 AND asset_id='metals:commodity:gold'
               GROUP BY record_type ORDER BY record_type""",
            (publication.publication_id,),
        )
        gold_counts = [(str(t), int(c)) for t, c in cursor.fetchall()]
        cursor.execute(
            """SELECT record_type, COUNT(*) FROM presentation_records
               WHERE publication_id=%s AND domain_id='metals'
                 AND asset_id='metals:vehicle:GLD'
               GROUP BY record_type ORDER BY record_type""",
            (publication.publication_id,),
        )
        gld_counts = [(str(t), int(c)) for t, c in cursor.fetchall()]
    print(f"POSTGRES_PRESENTATION_COUNTS={counts!r}")
    if counts != EXPECTED_COUNTS:
        raise RuntimeError("PostgreSQL presentation record populations do not reconcile.")
    print("POSTGRES_PRESENTATION_POPULATION_RECONCILIATION=PASS")
    print(f"GOLD_ASSET_DETAIL_COUNTS={gold_counts!r}")
    if not any(name == "metals_model_component" for name, _ in gold_counts):
        raise RuntimeError("Gold asset detail is missing Metals model-component evidence.")
    if not any(name == "metals_regime_probability" for name, _ in gold_counts):
        raise RuntimeError("Gold asset detail is missing Metals regime evidence.")
    print(f"GLD_ASSET_DETAIL_COUNTS={gld_counts!r}")
    if not any(name == "metals_uncertainty_adjusted" for name, _ in gld_counts):
        raise RuntimeError("GLD asset detail is missing uncertainty-adjusted evidence.")
    print("METALS_ASSET_DETAIL_TACTICAL_EVIDENCE=PASS")

    invalid = PresentationPublication(
        publication_id=publication.publication_id + "-invalid",
        publication_version=publication.publication_version,
        source_database_sha256=publication.source_database_sha256,
        source_database_classification=publication.source_database_classification,
        published_at_utc=publication.published_at_utc,
        publication_status="STAGED",
        records=tuple(
            record
            for record in publication.records
            if not (record.record_type == "domain_health" and record.domain_id == "metals")
        ),
    )
    failed = False
    try:
        publish_presentation_bundle(store, invalid)
    except PresentationPublicationError as exc:
        failed = True
        print(f"EXPECTED_INVALID_PUBLICATION_FAILURE={exc}")
    if not failed:
        raise RuntimeError("Invalid publication unexpectedly succeeded.")

    active_after = store.active_metadata()
    if not active_after:
        raise RuntimeError("Active publication disappeared after failed replacement.")
    if str(active_after["publication_id"]) != active_id:
        raise RuntimeError("Failed replacement displaced the last-good active publication.")
    if str(active_after["content_fingerprint"]) != active_fingerprint:
        raise RuntimeError("Last-good active fingerprint changed after failed replacement.")
    print("FAILED_REPLACEMENT_PRESERVES_LAST_GOOD=PASS")

    with psycopg.connect(dsn) as pg, pg.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM presentation_active_publication")
        active_pointer_count = int(cursor.fetchone()[0])
        cursor.execute("SELECT COUNT(*) FROM presentation_publications WHERE publication_status='ACTIVE'")
        active_publication_count = int(cursor.fetchone()[0])
        cursor.execute("SELECT COUNT(*) FROM presentation_publications WHERE publication_id=%s", (invalid.publication_id,))
        invalid_persisted = int(cursor.fetchone()[0])
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
        tables_after = [row[0] for row in cursor.fetchall()]
    if active_pointer_count != 1 or active_publication_count != 1:
        raise RuntimeError("Expected exactly one active presentation publication.")
    if invalid_persisted != 0:
        raise RuntimeError("Invalid semantic publication was persisted.")
    print("INVALID_PUBLICATION_NEVER_STAGED=PASS")

    non_presentation_after = {name for name in tables_after if not name.startswith("presentation_")}
    if non_presentation_after != existing_non_presentation:
        raise RuntimeError(
            "Existing application table set changed. "
            f"removed={sorted(existing_non_presentation - non_presentation_after)}; "
            f"added={sorted(non_presentation_after - existing_non_presentation)}"
        )
    print("EXISTING_POSTGRES_APPLICATION_TABLES_PRESERVED=PASS")
    print(f"PRIOR_ACTIVE_PUBLICATION_WAS={previous_id!r}")
    print(f"PRIOR_ACTIVE_FINGERPRINT_WAS={previous_fingerprint!r}")
    print("METALS_TACTICAL_PRESENTATION_POSTGRES_REHEARSAL=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
