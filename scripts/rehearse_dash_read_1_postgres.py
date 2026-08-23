"""Rehearse DASH-READ-1 presentation publication against hosted PostgreSQL/Neon."""

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

EXPECTED_COUNTS = [
    ("crypto", "asset", 6),
    ("crypto", "domain_health", 1),
    ("crypto", "forecast", 120),
    ("crypto", "recommendation", 6),
    ("crypto", "risk", 6),
    ("metals", "asset", 16),
    ("metals", "domain_health", 1),
    ("metals", "forecast", 16),
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
    print("UIP DASH-READ-1 — POSTGRESQL PRESENTATION STORE REHEARSAL")
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
    print(f"PRESENTATION_TABLES={presentation_tables!r}")
    if presentation_tables != expected_tables:
        raise RuntimeError("Unexpected PostgreSQL presentation table set.")

    duck = duckdb.connect(str(database), read_only=True)
    try:
        publication = build_presentation_publication(
            ROOT,
            database,
            duck,
            publication_id=f"dash-read-1-r3-certified-postgres-{expected_sha[:12]}",
            published_at_utc="2026-08-23T03:30:00+00:00",
        )
    finally:
        duck.close()

    validate_publication_bundle(publication)
    print(f"CERTIFIED_PUBLICATION_ID={publication.publication_id}")
    print(f"CERTIFIED_PUBLICATION_RECORD_COUNT={len(publication.records)}")
    print(f"CERTIFIED_PUBLICATION_FINGERPRINT={publication.content_fingerprint}")
    if publication.source_database_sha256 != expected_sha:
        raise RuntimeError("Certified publication source SHA changed.")
    if len(publication.records) != 4031:
        raise RuntimeError("Certified R3 presentation record count changed.")

    result = publish_presentation_bundle(store, publication)
    if result.status != "ACTIVE":
        raise RuntimeError("Certified publication did not activate.")
    active = store.active_metadata()
    print(f"PREVIOUS_ACTIVE_PUBLICATION={result.previous_active_publication_id!r}")
    print(f"ACTIVE_PUBLICATION_METADATA={active!r}")
    if not active:
        raise RuntimeError("PostgreSQL has no active presentation publication.")
    if active["publication_id"] != publication.publication_id:
        raise RuntimeError("Unexpected active publication ID.")
    if active["source_database_sha256"] != expected_sha:
        raise RuntimeError("Active PostgreSQL publication source SHA changed.")
    if int(active["record_count"]) != 4031:
        raise RuntimeError("Active PostgreSQL publication record count changed.")
    active_id = str(active["publication_id"])
    active_fingerprint = str(active["content_fingerprint"])
    print("CERTIFIED_POSTGRES_ACTIVATION=PASS")

    with psycopg.connect(dsn) as pg, pg.cursor() as cursor:
        cursor.execute(
            """SELECT domain_id, record_type, COUNT(*) FROM presentation_records
               WHERE publication_id=%s GROUP BY domain_id, record_type ORDER BY domain_id, record_type""",
            (publication.publication_id,),
        )
        counts = [(str(d), str(t), int(c)) for d, t, c in cursor.fetchall()]
    print(f"POSTGRES_PRESENTATION_COUNTS={counts!r}")
    if counts != EXPECTED_COUNTS:
        raise RuntimeError("PostgreSQL presentation record populations do not reconcile.")
    print("POSTGRES_PRESENTATION_POPULATION_RECONCILIATION=PASS")

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
        raise RuntimeError("Failed publication replaced last-good active version.")
    if str(active_after["content_fingerprint"]) != active_fingerprint:
        raise RuntimeError("Last-good publication fingerprint changed.")
    if active_after["publication_status"] != "ACTIVE":
        raise RuntimeError("Last-good publication is no longer ACTIVE.")
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

    print(f"ACTIVE_POINTER_COUNT={active_pointer_count}")
    print(f"ACTIVE_PUBLICATION_COUNT={active_publication_count}")
    print(f"INVALID_PUBLICATION_PERSISTED={invalid_persisted}")
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
    print("DASH_READ_1_POSTGRES_PRESENTATION_STORE_REHEARSAL=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
