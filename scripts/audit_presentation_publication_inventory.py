"""Read-only inventory of PostgreSQL presentation publications for regression recovery.

This command performs SELECT statements only. It does not stage, activate, reject,
update, insert, or delete presentation data.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

import psycopg


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    dsn = os.getenv("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is required")

    with psycopg.connect(dsn) as db:
        db.autocommit = False
        with db.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")

            cursor.execute("""
                SELECT p.publication_id,
                       p.publication_version,
                       p.source_database_sha256,
                       p.source_database_classification,
                       p.published_at_utc,
                       p.publication_status,
                       p.content_fingerprint,
                       p.record_count,
                       p.failure_reason,
                       CASE WHEN a.publication_id IS NOT NULL THEN TRUE ELSE FALSE END AS is_active,
                       a.activated_at_utc
                FROM presentation_publications p
                LEFT JOIN presentation_active_publication a
                  ON a.publication_id = p.publication_id AND a.singleton_id = 1
                ORDER BY p.published_at_utc DESC, p.publication_id DESC
            """)
            columns = [desc.name for desc in cursor.description]
            publications = [dict(zip(columns, row)) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT publication_id, domain_id, record_type, COUNT(*) AS record_count
                FROM presentation_records
                GROUP BY publication_id, domain_id, record_type
                ORDER BY publication_id, domain_id, record_type
            """)
            grouped: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(dict))
            for publication_id, domain_id, record_type, count in cursor.fetchall():
                grouped[str(publication_id)][str(domain_id)][str(record_type)] = int(count)

            cursor.execute("""
                SELECT publication_id,
                       COUNT(*) FILTER (WHERE record_type='mtg_premium_research') AS mtg_premium_research,
                       COUNT(*) FILTER (WHERE domain_id='metals' AND record_type='tactical_state') AS metals_tactical_state,
                       COUNT(*) FILTER (WHERE domain_id='metals' AND record_type='risk') AS metals_risk,
                       COUNT(*) FILTER (WHERE domain_id='metals' AND record_type='forecast') AS metals_forecast,
                       COUNT(*) FILTER (WHERE domain_id='mtg' AND record_type='native_authority') AS mtg_native_authority
                FROM presentation_records
                GROUP BY publication_id
                ORDER BY publication_id
            """)
            sentinel_counts = {
                str(row[0]): {
                    "mtg_premium_research": int(row[1]),
                    "metals_tactical_state": int(row[2]),
                    "metals_risk": int(row[3]),
                    "metals_forecast": int(row[4]),
                    "mtg_native_authority": int(row[5]),
                }
                for row in cursor.fetchall()
            }

            cursor.execute("""
                SELECT publication_id, record_type, COUNT(*) AS record_count
                FROM presentation_records
                WHERE domain_id='mtg'
                GROUP BY publication_id, record_type
                ORDER BY publication_id, record_type
            """)
            mtg_types: dict[str, dict[str, int]] = defaultdict(dict)
            for publication_id, record_type, count in cursor.fetchall():
                mtg_types[str(publication_id)][str(record_type)] = int(count)

            cursor.execute("""
                SELECT publication_id, record_type, COUNT(*) AS record_count
                FROM presentation_records
                WHERE domain_id='metals'
                GROUP BY publication_id, record_type
                ORDER BY publication_id, record_type
            """)
            metals_types: dict[str, dict[str, int]] = defaultdict(dict)
            for publication_id, record_type, count in cursor.fetchall():
                metals_types[str(publication_id)][str(record_type)] = int(count)

        db.rollback()

    active = next((p for p in publications if p["is_active"]), None)
    prior_rich_candidates = [
        p for p in publications
        if sentinel_counts.get(str(p["publication_id"]), {}).get("mtg_premium_research", 0) > 0
    ]

    payload = {
        "status": "UIP_PRESENTATION_PUBLICATION_INVENTORY_READ_ONLY_PASS",
        "read_only": True,
        "active_publication": active,
        "publication_count": len(publications),
        "publications": publications,
        "record_type_counts": grouped,
        "sentinel_counts": sentinel_counts,
        "mtg_record_type_counts": mtg_types,
        "metals_record_type_counts": metals_types,
        "prior_rich_candidates": prior_rich_candidates,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    print("UIP_PRESENTATION_PUBLICATION_INVENTORY=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
