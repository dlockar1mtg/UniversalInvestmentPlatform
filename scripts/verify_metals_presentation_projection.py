from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.presentation.publication_model import build_presentation_publication


EXPECTED_SHA256 = "dff98e56d27cbc5ef879c18939309c5ab8661fa8fa6dfe74e82537fd53954f7c"
EXPECTED_METALS_TACTICAL_COUNTS = {
    "metals_model_component": 64,
    "metals_regime_probability": 12,
    "metals_uncertainty_adjusted": 32,
    "metals_recommendation_change": 10,
    "metals_data_freshness": 21,
    "metals_platform_health": 1,
}
EXPECTED_TOTAL_RECORDS = 4171


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only verification of Metals tactical evidence projection into DASH-READ-1 publication records.")
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--expected-sha256", default=EXPECTED_SHA256)
    args = parser.parse_args()

    repository_root = args.repository_root.resolve()
    database = args.database.resolve()

    if repository_root != ROOT:
        raise RuntimeError(f"Repository root mismatch: script={ROOT} requested={repository_root}")

    before = sha256_file(database)
    if before.lower() != args.expected_sha256.lower():
        raise RuntimeError(f"Database SHA-256 mismatch: {before}")

    connection = duckdb.connect(str(database), read_only=True)
    try:
        publication = build_presentation_publication(
            repository_root,
            database,
            connection,
            publication_id="metals-tactical-projection-verification",
            published_at_utc="2026-08-24T00:00:00+00:00",
        )
    finally:
        connection.close()

    after = sha256_file(database)
    if after.lower() != before.lower():
        raise RuntimeError("Authoritative DuckDB changed during read-only presentation projection verification.")

    counts = Counter(record.record_type for record in publication.records if record.domain_id == "metals")
    observed_tactical = {key: counts.get(key, 0) for key in EXPECTED_METALS_TACTICAL_COUNTS}
    if observed_tactical != EXPECTED_METALS_TACTICAL_COUNTS:
        raise RuntimeError(f"Metals tactical presentation counts mismatch: {observed_tactical}")
    if len(publication.records) != EXPECTED_TOTAL_RECORDS:
        raise RuntimeError(f"Unexpected total presentation record count: {len(publication.records)}")
    if publication.source_database_sha256.lower() != args.expected_sha256.lower():
        raise RuntimeError("Presentation publication source SHA-256 is not the verified Metals authority.")

    payload = {
        "status": "PASS",
        "read_only": True,
        "database_sha256": after,
        "publication_source_sha256": publication.source_database_sha256,
        "publication_record_count": len(publication.records),
        "metals_tactical_record_counts": observed_tactical,
        "content_fingerprint": publication.content_fingerprint,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "tactical_posture_authorized": False,
        "next_decision": "AUTHORIZE_METALS_PRESENTATION_REPUBLICATION_REHEARSAL",
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
