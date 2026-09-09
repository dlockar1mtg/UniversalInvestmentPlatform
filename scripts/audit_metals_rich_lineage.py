"""Read-only lineage audit for the restored rich Metals presentation surfaces."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import psycopg

TARGET_PUBLICATION_ID = "mtg-lane-native-detail-enrichment-a71e6025c44e"
TARGET_RECORD_COUNT = 13929

RECORD_TYPES = (
    "metals_price_history",
    "metals_current_price",
    "metals_data_freshness",
    "metals_model_component",
    "metals_platform_health",
    "metals_recommendation_change",
    "metals_regime_probability",
    "metals_uncertainty_adjusted",
    "tactical_state",
    "risk",
    "metals_commodity_decision_explanation",
)

LINEAGE_TOKENS = (
    "source",
    "authority",
    "sha",
    "path",
    "run",
    "model",
    "version",
    "method",
    "date",
    "time",
    "as_of",
    "fresh",
    "generated",
    "updated",
)


def _lineage_subset(payload: dict[str, object]) -> dict[str, object]:
    selected: dict[str, object] = {}
    for key, value in payload.items():
        lowered = key.lower()
        if any(token in lowered for token in LINEAGE_TOKENS):
            selected[key] = value
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    dsn = os.getenv("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is required")

    evidence: dict[str, object] = {
        "status": "STARTED",
        "query_policy": "READ_ONLY_SELECT_ONLY",
        "postgres_write_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "target_publication_id": TARGET_PUBLICATION_ID,
        "record_types": {},
    }

    with psycopg.connect(dsn) as db:
        with db.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")

            cur.execute(
                """
                SELECT a.publication_id, p.publication_status, p.record_count,
                       p.content_fingerprint, p.source_database_sha256,
                       p.published_at_utc, a.activated_at_utc
                FROM presentation_active_publication a
                JOIN presentation_publications p USING (publication_id)
                WHERE a.singleton_id=1
                """
            )
            active = cur.fetchone()
            if active is None:
                raise RuntimeError("No active presentation publication exists")

            (
                active_id,
                active_status,
                active_count,
                fingerprint,
                source_sha,
                published_at,
                activated_at,
            ) = active

            if str(active_id) != TARGET_PUBLICATION_ID:
                raise RuntimeError(f"Unexpected active publication: {active_id}")
            if str(active_status) != "ACTIVE":
                raise RuntimeError(f"Active publication status is not ACTIVE: {active_status}")
            if int(active_count) != TARGET_RECORD_COUNT:
                raise RuntimeError(f"Unexpected active record count: {active_count}")

            evidence["active_publication"] = {
                "publication_id": str(active_id),
                "publication_status": str(active_status),
                "record_count": int(active_count),
                "content_fingerprint": str(fingerprint),
                "source_database_sha256": str(source_sha),
                "published_at_utc": str(published_at),
                "activated_at_utc": str(activated_at),
            }

            surfaces: dict[str, object] = {}
            for record_type in RECORD_TYPES:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM presentation_records
                    WHERE publication_id=%s AND domain_id='metals' AND record_type=%s
                    """,
                    (TARGET_PUBLICATION_ID, record_type),
                )
                count = int(cur.fetchone()[0])

                cur.execute(
                    """
                    SELECT DISTINCT key
                    FROM presentation_records r
                    CROSS JOIN LATERAL jsonb_object_keys(r.payload_json) AS key
                    WHERE r.publication_id=%s
                      AND r.domain_id='metals'
                      AND r.record_type=%s
                    ORDER BY key
                    """,
                    (TARGET_PUBLICATION_ID, record_type),
                )
                keys = [str(row[0]) for row in cur.fetchall()]

                cur.execute(
                    """
                    SELECT asset_id, record_key, payload_json
                    FROM presentation_records
                    WHERE publication_id=%s AND domain_id='metals' AND record_type=%s
                    ORDER BY record_key
                    LIMIT 3
                    """,
                    (TARGET_PUBLICATION_ID, record_type),
                )
                samples = []
                for asset_id, record_key, payload in cur.fetchall():
                    payload_dict = dict(payload)
                    samples.append(
                        {
                            "asset_id": asset_id,
                            "record_key": str(record_key),
                            "lineage_fields": _lineage_subset(payload_dict),
                        }
                    )

                cur.execute(
                    """
                    SELECT DISTINCT
                        NULLIF(payload_json->>'source_authority_path','') AS source_authority_path,
                        NULLIF(payload_json->>'source_authority_sha256','') AS source_authority_sha256,
                        NULLIF(payload_json->>'source_path','') AS source_path,
                        NULLIF(payload_json->>'source_sha256','') AS source_sha256,
                        NULLIF(payload_json->>'source_run_id','') AS source_run_id,
                        NULLIF(payload_json->>'run_id','') AS run_id,
                        NULLIF(payload_json->>'model_version','') AS model_version,
                        NULLIF(payload_json->>'methodology_version','') AS methodology_version
                    FROM presentation_records
                    WHERE publication_id=%s AND domain_id='metals' AND record_type=%s
                    ORDER BY 1,2,3,4,5,6,7,8
                    LIMIT 50
                    """,
                    (TARGET_PUBLICATION_ID, record_type),
                )
                lineage_rows = [
                    {
                        "source_authority_path": row[0],
                        "source_authority_sha256": row[1],
                        "source_path": row[2],
                        "source_sha256": row[3],
                        "source_run_id": row[4],
                        "run_id": row[5],
                        "model_version": row[6],
                        "methodology_version": row[7],
                    }
                    for row in cur.fetchall()
                ]

                surfaces[record_type] = {
                    "count": count,
                    "payload_keys": keys,
                    "sample_lineage": samples,
                    "distinct_standard_lineage": lineage_rows,
                }

            evidence["record_types"] = surfaces
            evidence["status"] = "METALS_RICH_LINEAGE_AUDIT_PASS"
            db.rollback()

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True, default=str))
    print("METALS_RICH_LINEAGE_AUDIT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
