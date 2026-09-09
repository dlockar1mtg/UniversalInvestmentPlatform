"""Read-only inventory of UIP-owned Metals source tables in PostgreSQL.

This diagnostic excludes presentation tables and performs no writes. It inventories
public tables whose names contain 'metals', their columns, exact row counts, and
min/max values for obvious date/timestamp columns so we can determine which rich
Metals presentation surfaces can be rebuilt from current UIP-owned authority.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import psycopg
from psycopg import sql

EXCLUDED_PREFIXES = ("presentation_",)
DATE_NAMES = (
    "as_of_date",
    "observation_date",
    "data_as_of_date",
    "forecast_origin_date",
    "generated_at_utc",
    "created_at_utc",
    "updated_at_utc",
    "ingested_at_utc",
    "collected_at_utc",
    "run_started_at_utc",
    "run_completed_at_utc",
)


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
        "tables": {},
    }

    with psycopg.connect(dsn) as db:
        db.autocommit = False
        with db.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public'
                  AND table_type='BASE TABLE'
                  AND table_name ILIKE '%metals%'
                ORDER BY table_name
                """
            )
            table_names = [str(row[0]) for row in cur.fetchall()]
            table_names = [
                name for name in table_names
                if not any(name.startswith(prefix) for prefix in EXCLUDED_PREFIXES)
            ]

            tables: dict[str, object] = {}
            for table_name in table_names:
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema='public' AND table_name=%s
                    ORDER BY ordinal_position
                    """,
                    (table_name,),
                )
                columns = [
                    {
                        "name": str(name),
                        "data_type": str(data_type),
                        "nullable": str(nullable) == "YES",
                    }
                    for name, data_type, nullable in cur.fetchall()
                ]
                column_names = [str(item["name"]) for item in columns]

                cur.execute(
                    sql.SQL("SELECT COUNT(*) FROM {}")
                    .format(sql.Identifier(table_name))
                )
                row_count = int(cur.fetchone()[0])

                ranges: dict[str, object] = {}
                for candidate in DATE_NAMES:
                    if candidate not in column_names:
                        continue
                    cur.execute(
                        sql.SQL("SELECT MIN({0})::text, MAX({0})::text FROM {1}")
                        .format(sql.Identifier(candidate), sql.Identifier(table_name))
                    )
                    minimum, maximum = cur.fetchone()
                    ranges[candidate] = {
                        "min": minimum,
                        "max": maximum,
                    }

                tables[table_name] = {
                    "row_count": row_count,
                    "columns": columns,
                    "date_ranges": ranges,
                }

            evidence["tables"] = tables
            evidence["table_count"] = len(tables)
            evidence["status"] = "METALS_NATIVE_SOURCE_INVENTORY_PASS"

        db.rollback()

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    print("METALS_NATIVE_SOURCE_INVENTORY=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
